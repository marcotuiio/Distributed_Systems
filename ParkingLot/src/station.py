import zmq
import threading
import time
import os
from queue import Queue, Empty
import uuid

from manager import STATIONS_FILE

####### TRAPACEANDO - Nao estou conseguind travar a eleição nas multiplas threads
####### Detectar a eleiçõ funciona bem, o problema esta sendo tratar da eleição, pois
####### todas as estações estão tentando tratar a eleição ao mesmo tempo e ai as portas
####### estao sobrecarregadas e o sistema quebra e nenhuma eleição é feita
####### Entao vou criar um lock global para todas as estações e tentar fazer a eleição

GLOBAL_LOCK_IN_ELECTION = threading.Lock()

RESPONSE_TIMEOUT = 5
PING_INTERVAL = 10
PING_RETRY = 3

# Fila global de carros em espera, será atualiza por mensagens de broadcast quando um carro chegar e não tiver vaga
# Entao de tempos em tempos as estações vão verificar se tem carro na fila e tentar alocar uma vaga
# Essa é a estrategia para tratar starvation e eventuais filas de espera

global_car_queue = Queue()

class Station:
    def __init__(self, station_id, ipaddr, port, manager_ip, manager_port, other_stations=[]):
        self.station_id = station_id
        self.ipaddr = ipaddr
        self.port = port
        self.status = 0
        self.last_ping = -1

        self.lock = threading.Condition()
        
        # Lista que guarda as conexões com as outras estações via BROADCAST
        self.connections = []

        self.nspots = 0
        # Lista do tipo (spot, car_id)
        self.local_spots = []

        # Fila para guardar as respostas dos pings e nao embaralhar com as ordens de execução
        self.ping_responses = Queue()
        
        self.context = zmq.Context()
        self.manager_socket = self.context.socket(zmq.REQ)
        self.manager_socket.connect(f"tcp://{manager_ip}:{manager_port}")

        self.broadcast_socket = self.context.socket(zmq.PUB)
        self.broadcast_socket.bind(f"tcp://{self.ipaddr}:{self.port}")

        self.subscriber_socket = self.context.socket(zmq.SUB)
        for other_ip, other_port in other_stations:
            if other_ip != self.ipaddr or other_port != self.port:
                self.subscriber_socket.connect(f"tcp://{other_ip}:{other_port}")
        self.subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")


    def activate_station(self):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                continue

            print(f"\nActivating station {self.station_id}")

            # Requisitando quantas estações estão ativas
            # Acho que dava pra remover esse request pro manager e fazer um broadcast pra todas as estações
            # Porem, acho mais facil ir direto aqui e ver se tem pelo menos uma estação ativa
            self.manager_socket.send_json({"type": "request_active_stations"})
            time.sleep(0.3)  

            active_stations = -1
            while True:
                try:
                    message = self.manager_socket.recv_json(flags=zmq.NOBLOCK)
                    if message["type"] == "response_active_stations":
                        active_stations = len(message["active_stations"])
                        break
                except zmq.Again:
                    break

            print(f"<<< Active stations before: {active_stations}")

            # Primeira estação a ser ativada
            if active_stations == 0:
                # Requisitar o total de vagas pro manager
                self.manager_socket.send_json({"type": "request_total_spots"})
                time.sleep(0.3)

                total_spots = 0
                while True:
                    try:
                        message = self.manager_socket.recv_json(flags=zmq.NOBLOCK)
                        if message["type"] == "response_total_spots":
                            total_spots = message["total_spots"]
                            break
                    except zmq.Again:
                        break

                # print(f"Total spots: {total_spots}")
                self.nspots = total_spots
                self.status = 1
                for i in range(total_spots):
                    self.local_spots.append((i, None)) 

                # Informar o manager que a estação foi ativada
                self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                response = self.manager_socket.recv_json()
                # print(f">> Manager response firts_station: {response}")

                self.connections = response["active_stations"]

                self.manager_socket.send_json({"type": "print_stations"})
                response = self.manager_socket.recv_json()

            elif active_stations > 0:
                # Da estação que mais tiver vagas, requisitar sua lista de vagas
                # Será que é melhor pedir do que tudo de uma vez so? Tipo, pedir o numero de vagas e a lista de vagas
                # ai ja tem tudo de uma vez. Ponto negativo é que vai demorar beeem mais pra todas as estações responderem

                # Mandar broadcast para todas as estações requisitando quantas vagas elas tem
                self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
                time.sleep(0.3)

                # Receber respostas das estações
                spots_info = []
                while True:
                    try:
                        message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                        if message["type"] == "response_spots":
                            spots_info.append(message)
                    except zmq.Again:
                        break
                
                if not spots_info:
                    print("No other stations responded to broadcast activation.\n")
                else:
                    max_spots_station = max(spots_info, key=lambda x: x["nspots"])
                    # print(f"Station with most spots: {max_spots_station['station_id']} = {max_spots_station['nspots']}\n\n")
                    self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": max_spots_station["station_id"]})
                    time.sleep(0.3)

                    # Receber a lista de vagas da estação com mais vagas
                    spots_list = []
                    while True:
                        try:
                            message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                            if message["type"] == "response_spots_list" and message["station_id"] == max_spots_station["station_id"]:
                                spots_list = message["spots_list"]
                                break
                        except zmq.Again:
                            break

                    # Distribuir as vagas seguindo a logica de divisão
                    # Se está ativando a primeira estação, todas as vagas são dela
                    # Senão, busca a estação com o maior número de vagas e divide as vagas pela metade
                    if spots_list:
                        half_spots, remainder = divmod(len(spots_list), 2)
                        self.local_spots = spots_list[:half_spots]
                        remaining_spots = spots_list[half_spots:]
                        # print(f"Half spots: {half_spots}, remainder: {remainder}\n\n")
                        # print(f"Station {self.station_id} spots: {self.local_spots}")
                        # print(f"Remaining spots: {remaining_spots}")
                        self.nspots = len(self.local_spots)
                        self.status = 1

                        # Mandar a nova lista de vagas para a estação que enviou
                        self.broadcast_socket.send_json({"type": "update_spots", "station_id": max_spots_station["station_id"], "spots_list": remaining_spots})
                        response = self.subscriber_socket.recv_json()
                        # print(f">> Station {max_spots_station['station_id']} response: {response}")

                        # Atualizar a lista de vagas da estação que enviou e da que requisitou
                        self.manager_socket.send_json({"type": "update_station_spots", "station_id": max_spots_station["station_id"], "spots": remaining_spots, "status": 1})
                        response = self.manager_socket.recv_json()
                        # print(f">> Manager response max_station: {response}")
                        self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                        response = self.manager_socket.recv_json()
                        # print(f">> Manager response new_station: {response}")

                        self.connections = response["active_stations"]

                        self.manager_socket.send_json({"type": "print_stations"})
                        response = self.manager_socket.recv_json()

            print(f"<<< Active stations after: {active_stations + 1}")
       
            # Ja que nao consegui fazer o manager funcionar so no ping
            # Vou enviar uma mensagem a todos assim que ativar a estação com a nova lista de conexões
            # Essa lista é recebida do manager sempre que uma estação é ativada ou desativada
            self.broadcast_socket.send_json({"type": "update_connections", "station_id": self.station_id, "connections": self.connections})
            time.sleep(0.3)

            print(f"<<< Station {self.station_id} known connections: {self.connections}\n")


    def ping(self):
        # Talvez nao seja a melhor maneira, mas servira por agora
        # A ideia é que a estação que falhar, não responderá ao ping
        # Ai tendo a lista de estações ativas com o manager, se uma estação não responder ao ping
        # O processo de eleição é disparado, visto que a estação ja foi artificialmente desativada
        while True:
            with self.lock:
                if GLOBAL_LOCK_IN_ELECTION.locked():
                    continue

                if self.status == 0:
                    continue
                
                if time.time() - self.last_ping < PING_INTERVAL:
                    continue

                try:
                    print(f"\n>>> Pinging station {self.station_id}")
                    ## Inicialmente a ideia era de que aqui tivesse uma comunicação com o manager pra saber 
                    ## quais estações estão ativas, mas tavlvez nao seja tao legal comunicar toda hora com ele,
                    # entao vou manter a lista de estações ativas na própria estação e fazer broadcast 
                    # para todas as estações ativas, assim é quase como uma overlay network

                    # Limpar a fila de respostas antes de enviar um novo ping
                    # e gerar um identificador único para o ping
                    # Sem esses passos, como existem varias thread e requisicoes iguais 
                    # em estações diferentes ocorre appends duplicados na fila de respostas 
                    # e estava quebrando todo o sistema
                    for i in range(PING_RETRY):
                        while not self.ping_responses.empty():
                            self.ping_responses.get()

                        ping_id = str(uuid.uuid4())

                        # Mandar ping para todas as estações ativas
                        self.broadcast_socket.send_json({"type": "ping", "station_id": self.station_id, "ping_id": ping_id})
                        time.sleep(0.5) # Dando um alivio para as outras estações responderem

                        # Receber respostas dos pings
                        responses = []
                        start_time = time.time()
                        while time.time() - start_time < RESPONSE_TIMEOUT:
                            try:
                                message = self.ping_responses.get_nowait()
                                if message["type"] == "ping_response" and message["ping_id"] == ping_id:
                                    # print(f"Received ping response from {message['station_id']} in station {self.station_id}")
                                    responses.append(message["station_id"])
                            except Empty:
                                time.sleep(0.1)

                        self.last_ping = time.time()
                        if len(self.connections) - 1 == len(responses):
                            print("\nAll stations are active")
                            print(f"<<< ({i}) Ping responses ({self.station_id}): {responses}")
                            print(f"<<< ({i}) Known connections ({self.station_id}): {self.connections}\n")
                            break
                    
                    if len(self.connections) - 1 > len(responses):
                        # Parar todos os pings e executar a eleição - estrategia trapaceira global, mas é a unica que nao quebra as threads
                        if GLOBAL_LOCK_IN_ELECTION.locked():
                            print("<<< Election already in progress")
                            continue

                        print("\nSome station is inactive")
                        print(f"<<< ({i}) Ping responses ({self.station_id}): {responses}")
                        print(f"<<< ({i}) Known connections ({self.station_id}): {self.connections}\n")

                        GLOBAL_LOCK_IN_ELECTION.acquire()

                        self.broadcast_socket.send_json({"type": "trigger_election", "station_id": self.station_id})
                        time.sleep(0.5)

                        responses.append(self.station_id)
                        dead_station_id = list(set(self.connections) - set(responses))[0]
                        print(f'!!!! Triggering election in station {self.station_id} - dead station {dead_station_id}')
                        self.election(dead_station_id, responses)

                except zmq.ZMQError as e:
                    print(f"ZMQError in ping: {e}")
                    time.sleep(1)  # Espera antes de tentar novamente


    # Apenas muda o status da estação para inativa - primeiro passo da simulacao de falha
    def deactivate_station(self):
        self.status = 0
        self.local_spots = []


    # Implementa o sistema de eleição, é uma simulação pois isso ocorre apoós um ping falhar mas 
    # antes a estação foi desativada manualmente
    def election(self, dead_station_id, active_stations):
        if GLOBAL_LOCK_IN_ELECTION.locked():
            print(f"<<< Deactivating station {dead_station_id} - detected by station {self.station_id}")

            # Ultima estação a ser desativada - condição impossivel (< 1) ja que esse codigo so vai rodar
            # se invocado por eleição disparada por outra estação, entao tem pelo menos 1 ativa ao fim
            
            # Como é uma falha simulada, deve ser antes identificada por ping para disparar a eleição
            # O critério de eleição adotado é dar as vagas da estação que falhou para a estação com menos vagas
            # Se houver empate, a primeira estação que tiver menos vagas herdará as vagas
            
            if len(active_stations) > 0:
                
                # Mandar broadcast para todas as estações requisitando quantas vagas elas tem e ter um timeout
                self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
                start_time = time.time()
                timeout = 1.0 

                spots_info = []
                spots_info.append((self.station_id, self.nspots))
                while len(spots_info) < len(active_stations):
                    try:
                        message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                        if message["type"] == "response_spots":
                            # print(f" **** Request spots from {message['station_id']} - received here {self.station_id} = {message['nspots']}")
                            spots_info.append((message['station_id'], message['nspots']))
                    except zmq.Again:
                        if time.time() - start_time > timeout and len(spots_info) < len(active_stations):
                            print(f"Timeout reached. {spots_info} responded. Retrying...")
                            self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
                            start_time = time.time()
                            time.sleep(0.1)

                # print(f"<<< Information about spots: {spots_info}\n")
                if not spots_info:
                    print("ERROR - No other stations responded to broadcast deactivation.\n")
                    exit(1)
                else:
                    min_spots_station = min(spots_info, key=lambda x: x[1])
                    print(f"Station with least spots (that answerd first): {min_spots_station[0]} = {min_spots_station[1]}")
                    self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": min_spots_station[0]})
                    time.sleep(0.1) 

                    # Receber a lista de vagas da estação com menos vagas
                    spots_list = []
                    while True:
                        try:
                            message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                            if message["type"] == "response_spots_list" and message["station_id"] == min_spots_station[0]:
                                spots_list = message["spots_list"]
                                break
                        except zmq.Again:
                            self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": min_spots_station[0]})
                            time.sleep(0.1)

                    # print(f"~~~~ Spots list: {spots_list}")

                    # Distribuir as vagas seguindo a logica de divisão
                    # A estacao com menos vagas herda as vagas da estacao que falhou
                    if spots_list:
                        retry = 0
                        while retry < PING_RETRY:
                            try:
                                self.manager_socket.send_json({"type": "request_spots_from_station", "station_id": dead_station_id})
                                response = self.manager_socket.recv_json()
                                dead_station_spots = response["spots"]
                                print(f"---- Dead station spots ({dead_station_id}): {dead_station_spots}")
                            
                                remaining_spots = spots_list + dead_station_spots
                            
                                # Remover a nova lista de vagas para a estação que falhou - Testar se precisa disso aqui, ou pode ser antes
                                # self.broadcast_socket.send_json({"type": "update_spots", "station_id": dead_station_id, "spots_list": []})
                                # response = self.subscriber_socket.recv_json()
                                if min_spots_station[0] == self.station_id:
                                    self.local_spots = remaining_spots
                                    self.nspots = len(self.local_spots)
                                else:
                                    self.broadcast_socket.send_json({"type": "update_spots", "station_id": min_spots_station[0], "spots_list": remaining_spots})
                                    response = self.subscriber_socket.recv_json()
                                # print(f">> Station {min_spots_station['station_id']} response: {response}")

                                # Atualizar a lista de vagas da estação que herdou as vagas e da que falhou com o manager
                                self.manager_socket.send_json({"type": "update_station_spots", "station_id": min_spots_station[0], "spots": remaining_spots, "status": 1})
                                response = self.manager_socket.recv_json()
                                self.manager_socket.send_json({"type": "update_station_spots", "station_id": dead_station_id, "spots": [], "status": 0})
                                response = self.manager_socket.recv_json()

                                self.connections = response["active_stations"]

                                print(f"\n<<< Active stations after deactivation: {len(active_stations)}")
                                self.broadcast_socket.send_json({"type": "update_connections", "station_id": self.station_id, "connections": self.connections})
                                time.sleep(0.3)
                                
                                self.manager_socket.send_json({"type": "print_stations"})
                                response = self.manager_socket.recv_json()

                                self.broadcast_socket.send_json({"type": "terminate_election"})
                                time.sleep(0.2)

                                print(f"<<< Station {self.station_id} known connections: {self.connections}")
                                print(f'!!!! Election finished in station {self.station_id} - dead station {dead_station_id}\n')

                                GLOBAL_LOCK_IN_ELECTION.release()
                                break

                            except zmq.ZMQError as e:
                                print(f"Failed to communicate with manager: {e}")
                                retry += 1
                                time.sleep(1)

    # Verifica se há vagas disponíveis na estação
    # Se houver, sinaliza verdadeiro e retorna o índice da vaga
    # Se não houver, sinaliza falso e retorna None
    def check_for_empty_spots(self):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                print(f"<<< Checking - Station {self.station_id} is in election")
                time.sleep(1)
                continue

            for spot_index, tuple in enumerate(self.local_spots):
                if tuple[1] is None: # Vaga vazia
                    return True, spot_index
            return False, None
    

    # Aloca uma vaga para um carro
    # Se houver vaga disponível, aloca a vaga e comunica ao manager sua nova lista de vagas
    # Se não houver vaga disponível, requisita uma vaga de outra estação e aguarda a resposta
    def allocate_spot(self, car_id):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                print(f"<<< Allocating - Station {self.station_id} is in election")
                time.sleep(1)
                continue

            sucess, spot_index = self.check_for_empty_spots()
            if sucess:
                spot = self.local_spots[spot_index][0] 
                self.local_spots[spot_index] = (spot, car_id)
                print(f"$$$ Station {self.station_id} allocated spot {spot} to car {car_id}")
                print(f"$$$ Station {self.station_id} spots: {self.local_spots}\n")

                # Informa manager da vaga com carro alocado
                self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                response = self.manager_socket.recv_json()

            elif not sucess:
                # A Estrategia adotada é requisitar vagas para as estações conhecidas até conseguir uma vaga
                print(f"\n:( Station {self.station_id} has no spots available")
                borrowed = False
                for con in self.connections:
                    if borrowed:
                        break
                    if con == self.station_id:
                        continue
                    print(f"### Requesting spot from station {con}")
                    self.broadcast_socket.send_json({"type": "car_borrow_spot", "in_need_station_id": self.station_id, "target_station_id": con, "car_id": car_id})
                    time.sleep(1) # Tempo que leva pra estação processar a requisição de emprestimo -> aqui costuma capotar
                    ## Talvez precise aumentar aqui, adicionar um verificador se a resposta foi processada e é falsa ou sequer foi processada
                    start_time = time.time()
                    while time.time() - start_time < (3 * RESPONSE_TIMEOUT):
                        try:
                            message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                            if message["type"] == "response_car_borrow_spot" and message["in_need_station_id"] == self.station_id:
                                if message["status"] == "success":
                                    print(f":D Station {self.station_id} borrowed spot from station {con}\n")
                                    self.broadcast_socket.send_json({"type": "confirmation_received", "station_id": con})
                                    borrowed = True
                                    break
                                elif message["status"] == "fail":
                                    break
                        except zmq.Again:
                            time.sleep(0.1)
                            continue
                
                if not borrowed:
                    print(f";-; No stations could lend a spot to station {self.station_id} - car {car_id}")
                    global_car_queue.put(car_id)
                    print(f";-; Car {car_id} is in queue\n")
                

    # Requisita uma vaga de outra estação
    # Se a estação requisitada tiver vaga disponível, aloca a vaga e comunica ao manager sua nova lista de vagas
    # Se a estação requisitada não tiver vaga disponível, sinaliza falso e retorna None para tentar com outra estação
    def borrow_spot(self, station_id, car_id):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                print(f"<<< Borrowing Station {self.station_id} is in election")
                time.sleep(1)
                continue

            sucess, spot_index = self.check_for_empty_spots()
            # Se essa estação possuir a vaga, ja aloca aqui mesmo e informa ao manager
            # A estaçao que requisitou a vaga é informada do sucesso quando voltar desse metodo
            if sucess:
                spot = self.local_spots[spot_index][0] 
                self.local_spots[spot_index] = (spot, car_id)
                print(f"%%% Station {self.station_id} lent spot {spot} to car {car_id} | Station {station_id} asked")
                print(f"%%% Station {self.station_id} spots: {self.local_spots}")
                
                # Informa manager da vaga com carro alocado
                self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                response = self.manager_socket.recv_json()
                return True

            elif not sucess:
                return False
        
    # Verifica se há um carro estacionado na estação
    # Se houver, sinaliza verdadeiro e retorna o índice da vaga
    # Se não houver, sinaliza falso e retorna None
    def look_for_car(self, car_id):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                print(f"<<< Looking - Station {self.station_id} is in election")
                time.sleep(1)
                continue

            for spot_index, tuple in enumerate(self.local_spots):
                if tuple[1] == car_id:
                    self.local_spots[spot_index] = (self.local_spots[spot_index][0], None)
                    print(f"*** Station {self.station_id} released spot {self.local_spots[spot_index][0]} from car {car_id}")
                    print(f"*** Station {self.station_id} spots: {self.local_spots}\n")
                    self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                    response = self.manager_socket.recv_json()
                    return True
            return False


    # Libera uma vaga de estacionamento
    # Broadcast para todas as estações para que elas busquem pelo carro e ja liberem a vaga
    def release_car(self, car_id):
        with self.lock:
            while GLOBAL_LOCK_IN_ELECTION.locked():
                print(f"<<< Releasing - Station {self.station_id} is in election")
                time.sleep(1)
                continue

            self.broadcast_socket.send_json({"type": "release_car", "leaving_station_id": self.station_id, "car_id": car_id})
            time.sleep(0.5) # Tempo para as estações processarem a requisição

            self.manager_socket.send_json({"type": "print_stations"})
            response = self.manager_socket.recv_json()


    # Lida com as requisições de outras estações e é uma thread separada
    # Requisições possíveis:
    # - request_spots: Requisição do número de vagas da estação, apenas responde com o número de vagas
    # - request_spots_list: Requisição da lista de vagas da estação, apenas responde com a lista de vagas
    # - update_spots: Atualização da lista de vagas da estação, apenas atualiza a lista de vagas
    # - ping: Requisição de ping, checa se a estação está ativa e responde com um ping_response
    # - ping_response: Resposta ao ping apenas para garantir a ordem da fila de respostas
    # - trigger_election: Disparo de eleição nao esta sendo usada mas é uma mensagem de broadcast
    # - terminate_election: Terminar eleição nao esta sendo usada mas é uma mensagem de broadcast
    # - reactivate_station: Teste para reativar a estação
    # - car_request_spot: Aloca de vaga da estação para um carro, apenas chama o método allocate_spot (ela entra pela estação que chama o metodo)
    # - car_borrow_spot:  Emprestimo de vaga em outra estaçao para um carro, se sucesso confirma com a estação requisitante
    # - release_car: Liberação de vaga, todas as estações buscam pelo carro mas apenas a que o encontrar o libera e informa ao manager
    def handle_requests(self):
        while self.status == 1:  # Enquanto a estação estiver ativa
            try:
                message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                
                if message["type"] == "request_spots":
                    # print(f"Request spots from {message['station_id']} - received here {self.station_id} = {self.nspots}")
                    self.broadcast_socket.send_json({"type": "response_spots", "station_id": self.station_id, "nspots": self.nspots})
            
                elif message["type"] == "request_spots_list" :
                    if message["target_station_id"] == self.station_id:
                        # print(f"Request spots list from {message['station_id']} - received here {self.station_id} => list: {self.local_spots}")
                        self.broadcast_socket.send_json({"type": "response_spots_list", "station_id": self.station_id, "spots_list": self.local_spots})
                
                elif message["type"] == "update_spots":
                    if message["station_id"] == self.station_id: 
                        # print(f"Update spots received here {self.station_id} - list: {self.local_spots} x new list: {message['spots_list']}")
                        self.local_spots = message["spots_list"]
                        self.nspots = len(self.local_spots)
                        self.broadcast_socket.send_json({"type": "response_update_spots", "station_id": self.station_id, "status": "success"})
        
                elif message["type"] == "update_connections":
                    # print(f"Updating connections {message['station_id']} - received here {self.station_id}")
                    # print(f"Old connections: {self.connections} x New connections: {message['connections']}")
                    self.connections = message["connections"]
                    self.broadcast_socket.send_json({"type": "responseupdate_connections", "station_id": self.station_id, "status": "success"})

                elif message["type"] == "ping" and message["station_id"] != self.station_id:
                    # print(f"Received ping from {message['station_id']} in station {self.station_id}")
                    self.broadcast_socket.send_json({"type": "ping_response", "station_id": self.station_id, "ping_id": message["ping_id"]})
                
                elif message["type"] == "ping_response":
                    self.ping_responses.put(message)
                    # time.sleep(0.2)                         

                elif message["type"] == "trigger_election":
                    # print(f"Received election trigger from {message['station_id']} in station {self.station_id}")
                    self.broadcast_socket.send_json({"type": "response_trigger_election", "station_id": self.station_id, "status": "success"})

                elif message["type"] == "terminate_election":
                    # print(f"Received election termination in station {self.station_id}")
                    self.broadcast_socket.send_json({"type": "response_terminate_election", "station_id": self.station_id, "status": "success"})

                # elif message["type"] == "reactivate_station" and self.status == 0 and self.station_id == message["station_id"]: ### Arrumar self.status aqui
                #     self.activate_station()
                #     self.broadcast_socket.send_json({"type": "response_reactivate_station", "station_id": self.station_id, "status": "success"})

                elif message["type"] == "car_request_spot" and message["station_id"] == self.station_id:
                    print(f"Received car request spot from {message['car_id']} in station {self.station_id}")
                    self.allocate_spot(message["car_id"])

                elif message["type"] == "car_borrow_spot" and message["target_station_id"] == self.station_id:
                    print(f"\nReceived car borrow spot from {message['in_need_station_id']} here in station {self.station_id} = car {message['car_id']}")
                    success = self.borrow_spot(message["in_need_station_id"], message["car_id"])

                    # Nesse ponto existe uma troca interessante a ser avaliada: como precisa informar a estação que requisitou e isso
                    # depende do tempo de processamento envio e resposta, a estação que requisitou pode ficar esperando muito pra
                    # garantir que quando voltar terá a resposta. Ou assim nao deixa a estação que requisitou esperando e se a resposta
                    # estiver pronta começa a disparar e receber as mensagens de confirmação e esperar que a requisitante confirme
                    # So assim, consegui garantir que a estação requisitante recebeu a resposta e nao travo o sistema, mas mantenho todos
                    # os sistemas para sair e buscar em outras estações 
                    while True: 
                        print(f"### Sending response to station {message['in_need_station_id']}")
                        self.broadcast_socket.send_json({"type": "response_car_borrow_spot", "in_need_station_id": message["in_need_station_id"], "station_id": self.station_id, "status": "success" if success else "fail"})
                        time.sleep(0.2)
                        response = self.subscriber_socket.recv_json()
                        if response["type"] == "confirmation_received" and response["station_id"] == self.station_id:
                            break

                elif message["type"] == "release_car":
                    print(f"Received release car from {message['car_id']} in station {self.station_id}")
                    success = self.look_for_car(message["car_id"])
                    if success:
                        print(f"*** Car left on station {message['leaving_station_id']}")
                    self.broadcast_socket.send_json({"type": "response_release_car", "station_id": self.station_id, "status": "success" if success else "fail"})

                elif message["type"] == "response_release_car":
                    pass

            except zmq.Again:
                time.sleep(0.1) # Descanso para não sobrecarregar o processador


    def run(self):
        self.activate_station()
        self.last_ping = time.time()
        request_thread = threading.Thread(target=self.handle_requests)
        request_thread.start()

        ping_thread = threading.Thread(target=self.ping)
        ping_thread.start()

        return request_thread, ping_thread
    

if __name__ == "__main__":
    manager_ip="127.0.0.1"
    manager_port=5555

    ### Atualmente as estações nao passam pelo estado de hibernação
    ### assim que o arquivos do manager é lido elas sao ativas -> ver como corrigir isso
    ### por algum motivo se as estações nao sao ativadas no momento da criação 
    ### da um bug sinistro que clona as variavel no estado inicial e nao deixa atualizar

    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path, "..")
    stations_file = os.path.join(path, STATIONS_FILE)
    stations = []
    with open(stations_file, "r") as file:
        for line in file:
            station_id, ipaddr, port = line.strip().split(" ")
            stations.append((station_id, ipaddr, int(port)))
    
    stations_obj = []
    for station_id, ipaddr, port in stations:
        other_stations = [(s[1], s[2]) for s in stations if s[0] != station_id]
        # print(f"Station {station_id} - IP: {ipaddr} - Port: {port} - Other stations: {other_stations}")
        s = Station(
            station_id=station_id,
            ipaddr=ipaddr,
            port=port,
            manager_ip=manager_ip,
            manager_port=manager_port,
            other_stations=other_stations
        )
        s.run()
        stations_obj.append(s)
        # time.sleep(1)


    # time.sleep(10)
    # station1.deactivate_station()

    ## TESTANDO REATIVAR A ESTAÇÃO - dependencia esquisita dos tempos de thread
    # time.sleep(30)
    # while GLOBAL_LOCK_IN_ELECTION.locked():
    #     continue
    # station2.broadcast_socket.send_json({"type": "reactivate_station", "station_id": "Station1"})
    # time.sleep(0.3)
    # # response = station2.subscriber_socket.recv_json()
    # print(f"Station2 response: {response}")

    # time.sleep(8)
    

    # Testando alocar vaga - carros sao threads
    # car1 = threading.Thread(target=station1.allocate_spot, args=("Car1",))
    # time.sleep(1)
    # car1.daemon = True
    # car1.start()

    ## Esse teste assim faz com eventualmente a estacao 1 trave nessa thread mas ok depois resolvo
    # for i in range(5):
    #     time.sleep(5)
    #     print(f"\n -->> Car{i}")
    #     car = threading.Thread(target=station1.allocate_spot, args=(f"Car{i}",))
    #     car.daemon = True
    #     car.start()
    #     car.join()

    # time.sleep(6)
    # print("\n==== Going to release car\n")
    # station2.release_car("Car2")