import zmq
import threading
import concurrent.futures
import time
import os
import sys
from queue import Queue, Empty
import uuid

# from app import App
from manager import STATIONS_FILE, manager_ip, manager_port


## Aumentar esse tempos pode atrasar o sistema mas evitar dalsas detecções de falha
## Aumentar o retry auumenta consideravelmete o fluxo de mensagens, porem apenas o response_timeout
## pode nao ser o suficiente para sync das threads e dar pra todas responderem
## A MEDIDA QUE MAIS ESTAÇÕES ESTIVEREM ATIVAS, MAIS TEMPO DEVE SER DADO PARA AS RESPOSTAS
# response_timeout = 3
DEFAULT_TIMEOUT = 3
PING_RETRY = 4

## Aumentar aqui pode atrasar muito a detecção de eleições mas diminuir MUITO o fluxo de mensagens
## ja que foi adotado um heartbeat distribuido de 10 UT, isto é, todas as estações perguntam a todas
PING_INTERVAL = 25

# Fila global de carros em espera, será atualiza por mensagens de broadcast quando um carro chegar e não tiver vaga
# Entao de tempos em tempos as estações vão verificar se tem carro na fila e tentar alocar uma vaga NAO FAZ ISSO
# Essa é a estrategia para tratar starvation e eventuais filas de espera

global_car_queue = Queue()

class Station:
    def __init__(self, station_id, ipaddr, port, manager_ip, manager_port, other_stations=[]):
        self.station_id = station_id
        self.ipaddr = ipaddr
        self.port = port
        self.status = 0
        self.last_ping = -1

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Lista que guarda as conexões com as outras estações via BROADCAST
        self.connections = []

        self.nspots = 0
        # Lista do tipo (spot, car_id)
        self.local_spots = []

        # Fila para guardar as respostas dos pings e nao embaralhar com as ordens de execução
        self.ping_responses = Queue()
        
        self.internal_requests = Queue()
        self.external_requests = Queue()

        self.in_election = False
        self.election_time = 0
        # self.election_proposals = None

        self.current_car = None
        self.current_station_borrowing = None
        self.current_status_borrowing = None
        self.current_spot_borrowing = None
        
        self.context = zmq.Context()
        self.manager_socket = self.context.socket(zmq.REQ)
        self.manager_socket.connect(f"tcp://{manager_ip}:{manager_port}")

        self.app_socket = self.context.socket(zmq.REP)
        self.app_socket.bind(f"tcp://{self.ipaddr}:{self.port-1}")
        # self.app_socket = self.context.socket(zmq.REP)
        # self.app_socket.bind(f"tcp://{self.ipaddr}:{self.port-2}")

        self.broadcast_socket = self.context.socket(zmq.PUB)
        self.broadcast_socket.bind(f"tcp://{self.ipaddr}:{self.port}")

        self.subscriber_socket = self.context.socket(zmq.SUB)
        for other_ip, other_port in other_stations:
            if other_ip != self.ipaddr or other_port != self.port:
                self.subscriber_socket.connect(f"tcp://{other_ip}:{other_port}")
        self.subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")


    def activate_station(self):
        while self.in_election:
            continue

        print(f"\nActivating station {self.station_id}")

        # Requisitando quantas estações estão ativas
        # Acho que dava pra remover esse request pro manager e fazer um broadcast pra todas as estações
        # Porem, acho mais facil ir direto aqui e ver se tem pelo menos uma estação ativa
        self.manager_socket.send_json({"type": "request_active_stations"})
        time.sleep(0.2)  

        active_stations = -1
        while active_stations == -1:
            try:
                message = self.manager_socket.recv_json(flags=zmq.NOBLOCK)
                if message["type"] == "response_active_stations":
                    active_stations = len(message["active_stations"])
                    break
            except zmq.Again:
                continue

        print(f"<<< Active stations before: {active_stations}")

        # Primeira estação a ser ativada
        if active_stations == 0:
            # Requisitar o total de vagas pro manager
            self.manager_socket.send_json({"type": "request_total_spots"})
            time.sleep(0.2)

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
            self.last_ping = time.time()
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

            # Limpar lixos anteriores na socket antes de começar !!! SERIO, ISSO É IMPORTANTE E DEMOREI MUITO PRA DESCOBRI
            while True:
                try:
                    message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                except zmq.Again:
                    break
            
            # Mandar broadcast para todas as estações requisitando quantas vagas elas tem
            self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
            # time.sleep(0.5)
            start_time = time.time()

            # Receber respostas das estações
            spots_info = []
            received_set = set()
            while len(spots_info) < active_stations:
                # time.sleep(0.5)
                try:
                    message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)           
                    # print(f"Received message: {message}")             
                    if message["type"] == "response_spots" and message["station_id"] not in received_set:
                        # print(f" **** Request spots from {message['station_id']} - received here {self.station_id} = {message['nspots']}")
                        spots_info.append(message)
                        received_set.add(message["station_id"])
                except zmq.Again:
                    if time.time() - start_time > DEFAULT_TIMEOUT and len(spots_info) < active_stations:
                        time.sleep(0.5)
                        print(f"(1) Timeout reached. {len(spots_info)} responded. Retrying...")
                        self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
                        start_time = time.time()
                        continue
            
            if not spots_info:
                print("ERORRR No other stations responded to broadcast activation.\n")
            else:
                # print(f"<<< Information about spots: {spots_info}\n")
                max_spots_station = max(spots_info, key=lambda x: x["nspots"])
                print(f"Station with most spots: {max_spots_station['station_id']} = {max_spots_station['nspots']}")
                self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": max_spots_station["station_id"]})
                time.sleep(0.3)

                # Receber a lista de vagas da estação com mais vagas
                spots_list = []
                while True:
                    try:
                        message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                        if message["type"] == "response_spots_list" and message["station_id"] == max_spots_station["station_id"]:
                            # print(f"Received spots list from station with most spots -> {message['station_id']} {message['spots_list']}")
                            spots_list = message["spots_list"]
                            break
                    except zmq.Again:
                        # print(f"Retrying request spots list from station {max_spots_station['station_id']}")
                        self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": max_spots_station["station_id"]})
                        time.sleep(0.3)
                        continue

                # Distribuir as vagas seguindo a logica de divisão
                # Se está ativando a primeira estação, todas as vagas são dela
                # Senão, busca a estação com o maior número de vagas e divide as vagas pela metade
                if spots_list and len(spots_list) > 1:
                    print(f" = Spots list: {spots_list}")
                    half_spots, remainder = divmod(len(spots_list), 2)
                    self.local_spots = spots_list[:half_spots]
                    remaining_spots = spots_list[half_spots:]
                    # print(f"Half spots: {half_spots}, remainder: {remainder}\n\n")
                    # print(f"Station {self.station_id} spots: {self.local_spots}")
                    # print(f"Remaining spots: {remaining_spots}")
                    self.nspots = len(self.local_spots)
                    self.last_ping = time.time()

                    # Mandar a nova lista de vagas para a estação que enviou
                    self.broadcast_socket.send_json({"type": "update_spots", "station_id": max_spots_station["station_id"], "spots_list": remaining_spots})
                    time.sleep(0.2)
                    # response = self.subscriber_socket.recv_json()
                    while True:
                        try:
                            message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                            if message["type"] == "response_update_spots" and message["station_id"] == max_spots_station["station_id"]:
                                print(f'\t>>>>> Confirmation received from station {message["station_id"]}')
                                break
                        except zmq.Again:
                            # print(f"Retrying update spots to station {max_spots_station['station_id']}")
                            time.sleep(0.4)
                            self.broadcast_socket.send_json({"type": "update_spots", "station_id": max_spots_station["station_id"], "spots_list": remaining_spots})
                            continue

                    # Atualizar a lista de vagas da estação que enviou e da que requisitou
                    self.manager_socket.send_json({"type": "update_station_spots", "station_id": max_spots_station["station_id"], "spots": remaining_spots, "status": 1})
                    response = self.manager_socket.recv_json()
                    # print(f">> Manager response max_station: {response}")
                    self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                    response = self.manager_socket.recv_json()
                    # print(f">> Manager response new_station: {response}")

                    self.connections = response["active_stations"]
                    self.status = 1

                    self.manager_socket.send_json({"type": "print_stations"})
                    response = self.manager_socket.recv_json()

        print(f"<<< Active stations after: {active_stations + 1}")
    
        # Vou enviar uma mensagem a todos assim que ativar a estação com a nova lista de conexões
        # Essa lista é recebida do manager sempre que uma estação é ativada ou desativada
        self.broadcast_socket.send_json({"type": "update_connections", "station_id": self.station_id, "connections": self.connections})
        time.sleep(0.3)

        print(f"<<< Station {self.station_id} known connections: {self.connections}\n")
        # response_timeout = DEFAULT_TIMEOUT * len(self.connections)
        return "Success"


    def ping(self):
        # Talvez nao seja a melhor maneira, mas servira por agora
        # A ideia é que a estação que falhar, não responderá ao ping
        # Ai tendo a lista de estações ativas com o manager, se uma estação não responder ao ping
        # O processo de eleição é disparado, visto que a estação ja foi artificialmente desativada
        while True:
            while self.in_election:
                time.sleep(2)
                continue

            if self.status == 0:
                time.sleep(1)
                continue

            # Tentando garantir que todas as estações tenham sido ligadas antes de começar a pingar
            # Senao ia começar o ping tendo 4 estaçoes conhecidas e terminar tendo 8 e ai problema
            # if time.time() - creation_time < FIRST_PING:
            #     time.sleep(1)
            #     continue

            if time.time() - self.last_ping < PING_INTERVAL:
                time.sleep(1)
                continue

            try:
                # print(f"\n>>> Pinging station {self.station_id}")
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
                    if self.status == 0:
                        break
                    if self.in_election:    
                        break
                    while not self.ping_responses.empty():
                        self.ping_responses.get()

                    ping_id = str(uuid.uuid4())

                    # Mandar ping para todas as estações ativas
                    self.broadcast_socket.send_json({"type": "ping", "station_id": self.station_id, "ping_id": ping_id})
                    time.sleep((len(self.connections) / 2) + 1) # Dando um alivio para as outras estações responderem

                    # DEBUG
                    # with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                    #     f.write(f"\n ({self.station_id}) PING {i}\n")
                    # Receber respostas dos pings
                    responses = []
                    while True:
                        try:
                            message = self.ping_responses.get_nowait()
                            if message["type"] == "ping_response" and message["ping_id"] == ping_id:
                                responses.append(message["station_id"])
                        except Empty:
                            break
                    
                    # DEBUG
                    with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                        f.write(f"\n ({self.station_id}) PING {i} {responses}\n")
                    self.last_ping = time.time()
                    if len(responses) == 0: ### PROBLEMAO, depois que alguem sai da vaga, as estações demoram pra responder
                        time.sleep(1)
                        break
                    if len(self.connections) - 1 == len(responses):
                        with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                            f.write(f"\n ({self.station_id}) PING {i} ALL STATIONS ARE ACTIVE\n")
                        # print("\nAll stations are active")
                        # print(f"<<< ({i}) Ping responses ({self.station_id}): {responses}")
                        # print(f"<<< ({i}) Known connections ({self.station_id}): {self.connections}\n")
                        break
                    print(f'<<< ({i}) Ping Retry - Station {self.station_id} got {len(responses)} responses expected {len(self.connections) - 1}')
    

                # if len(self.connections) - 1 > len(responses):
                if len(self.connections) - 1 - len(responses) == 1: ## SO CONSIGO DETECTAR E DISPARAR ELEIÇÃO SE UMA ESTAÇÃO FALHAR
                    if self.in_election:
                        print(f"<<< {self.station_id} Election already in progress")
                        continue

                    self.election_time = time.time()
                    self.broadcast_socket.send_json({"type": "trigger_election", "station_id": self.station_id, "time": self.election_time})

                    # DEBUG
                    with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                        f.write(f"\n ({self.station_id}) PING {self.last_ping} SOME STATION IS INACTIVE\n")
                        f.write(f"<<< ({i}) Ping responses ({self.station_id}): {responses}\n")
                        f.write(f"<<< ({i}) Known connections ({self.station_id}): {self.connections}\n")

                    print("\nSome station is inactive")
                    print(f"<<< ({i}) Ping responses ({self.station_id}): {responses}")
                    print(f"<<< ({i}) Known connections ({self.station_id}): {self.connections}\n")

                    print(f"<<< Detected failure {self.station_id} with time {self.election_time}")
                    responses.append(self.station_id)
                    dead_station_id = list(set(self.connections) - set(responses))[0]
                    # DEBUG
                    with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                        f.write(f"\n ELECTION START in {self.station_id} - dead {dead_station_id}\n")
                    print(f'!!!! Triggering election in station {self.station_id} - dead station {dead_station_id}')
                    # if not self.in_election :
                    self.in_election = True
                    self.election(dead_station_id, responses)


            except zmq.ZMQError as e:
                print(f"ZMQError in ping: {e}")
                time.sleep(1)  # Espera antes de tentar novamente


    # Apenas muda o status da estação para inativa - primeiro passo da simulacao de falha
    def deactivate_station(self):
        self.status = 0
        self.local_spots = []


    # Implementa o sistema de eleição, é uma simulação pois isso ocorre após 
    # um ping falhar mas antes a estação foi desativada manualmente
    def election(self, dead_station_id, active_stations):
        if self.in_election:
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
                            print(f"(2) Timeout reached. {len(spots_info)} responded. Retrying...")
                            self.broadcast_socket.send_json({"type": "request_spots", "station_id": self.station_id})
                            start_time = time.time()
                            # time.sleep(0.2)
                            continue

                # print(f"<<< Information about spots: {spots_info}\n")
                if not spots_info:
                    print("ERROR - No other stations responded to broadcast deactivation.\n")
                    exit(1)
                else:
                    min_spots_station = min(spots_info, key=lambda x: x[1])
                    spots_list = []

                    print(f"Station with least spots (that answerd first): {min_spots_station[0]} = {min_spots_station[1]}")
                    
                    # Se a propria estação for a que tem menos vagas, ela herda as vagas da estação que falhou e nem precisa enviar requests
                    if min_spots_station[0] == self.station_id:
                        spots_list = self.local_spots
                    
                    else:
                        self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": min_spots_station[0]})
                        # time.sleep(0.2) 
                        start = time.time()

                        # Receber a lista de vagas da estação com menos vagas
                        while True:
                            try:
                                message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                                if message["type"] == "response_spots_list" and message["station_id"] == min_spots_station[0]:
                                    spots_list = message["spots_list"]
                                    break
                            except zmq.Again:
                                if time.time() - start > DEFAULT_TIMEOUT:
                                    print(f"<<< (3) Timeout retrying request spots list from station {min_spots_station[0]} to continue election")
                                    start = time.time()
                                    self.broadcast_socket.send_json({"type": "request_spots_list", "station_id": self.station_id, "target_station_id": min_spots_station[0]})
                                continue

                    # print(f"= Spots list: {spots_list}\n")

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

                                print(f"<<< Active stations after deactivation: {len(active_stations)}")
                                self.broadcast_socket.send_json({"type": "update_connections", "station_id": self.station_id, "connections": self.connections})
                                time.sleep(0.3)
                                
                                self.manager_socket.send_json({"type": "print_stations"})
                                response = self.manager_socket.recv_json()

                                self.broadcast_socket.send_json({"type": "terminate_election"})
                                time.sleep(0.2)

                                print(f"<<< Station {self.station_id} known connections: {self.connections}")
                                print(f'!!!! Election finished in station {self.station_id} - dead station {dead_station_id}\n')
                                with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                                    f.write(f"\n ELECTION END in {self.station_id} - dead {dead_station_id}\n")

                                # response_timeout = DEFAULT_TIMEOUT * len(self.connections)

                                self.in_election = False
                                self.election_time = 0
                                # self.election_proposals = {}
                                break

                            except zmq.ZMQError as e:
                                print(f"Failed to communicate with manager: {e}")
                                retry += 1
                                time.sleep(1)
                    else:
                        print("ERROR - No spots list received from station with least spots\n")
                        exit(1)


    # Verifica se há vagas disponíveis na estação
    # Se houver, sinaliza verdadeiro e retorna o índice da vaga
    # Se não houver, sinaliza falso e retorna None
    def check_for_empty_spots(self):
        while self.in_election:
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
        while self.in_election:
            print(f"<<< Allocating - Station {self.station_id} is in election")
            time.sleep(1)
            continue
        
        start = time.time()
        sucess, spot_index = self.check_for_empty_spots()
        if sucess:
            spot = self.local_spots[spot_index][0] 
            self.local_spots[spot_index] = (spot, car_id)
            print(f"$$$ Station {self.station_id} allocated spot {spot} to car {car_id} in {time.time() - start} seconds")
            print(f"$$$ Station {self.station_id} spots: {self.local_spots}\n")

            # Informa manager da vaga com carro alocado
            self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
            response = self.manager_socket.recv_json()

        elif not sucess:
            # A Estrategia adotada é requisitar vagas para as estações conhecidas até conseguir uma vaga
            print(f"\n:( Station {self.station_id} has no spots available")
            borrowed = False
            futures = []

            ## ISSO AQUI É BEM RUIM EM OTIMIZAÇÕES DE TEMPO, POIS COMO TENTA LINEARMENTE, PODE DEMORAR O(ESTAÇÕES OCUPADAS + 1)
            ## A SOLUÇÃO SERIA FAZER UM BROADCAST PARA TODAS AS ESTAÇÕES E ESPERAR A RESPOSTA DE TODAS, MAS ISSO GERAO PROBLEMA DE PRECISAR
            ## CONFIMAR COM QUEM RESERVOU PARA NAO ALOCAR MAIS DE UMA VEZ PRO MESMO CARRO
            for con in self.connections:
                if borrowed:
                    break
                if con == self.station_id:
                    continue

                # futures.append(self.executor.submit(self.request_spot, con, car_id, start))
            # for future in concurrent.futures.as_completed(futures):
            #     if future.result():
            #         # Confrimar com essa estação que a vaga foi alocada e liberar as vagas reservadas de qualquer outra estação
            #         borrowed = True
            #         break

                print(f"### Requesting spot from station {con}")
                self.broadcast_socket.send_json({"type": "car_borrow_spot", "in_need_station_id": self.station_id, "target_station_id": con, "car_id": car_id, "start_time": start})

                while True:
                    if self.current_car == car_id and self.current_station_borrowing == con:
                        if self.current_status_borrowing == "success":
                            full_time = time.time() - start
                            print(f":D {self.station_id} borrowed spot to {car_id} from station {con} - FULL TIME {full_time:.4f} seconds\n")
                            borrowed = True
                            self.current_car = None
                            self.current_station_borrowing = None
                            self.current_status_borrowing = None
                            break

                        elif self.current_status_borrowing == "fail":
                            # print(f";-; Station {con} could not lend a spot to station {self.station_id} - car {car_id}")
                            break
                    
            if not borrowed:
                elapsed = time.time() - start
                print(f";-; No stations could lend a spot to station {self.station_id} - car {car_id} in {elapsed:.4f} seconds")
                global_car_queue.put(car_id)
                print(f";-; Car {car_id} is in queue\n")


    # Executada como uma thread separada pelo ThreadExecutor
    # Apenas tenta emprestar uma vaga para o carro contido na mensagem
    # Se conseguir aloca aqui mesmo e informa o manager
    # Se nao tiver vagas disponiveis apenas retorna para quem pediu a vaga inicialmente
    def borrow_spot(self, message):
        success, spot_index = self.check_for_empty_spots()
                
        self.broadcast_socket.send_json({"type": "response_car_borrow_spot", "in_need_station_id": message["in_need_station_id"], "station_id": self.station_id, "status": "success" if success else "fail", "spot_index": spot_index, "car_id": message["car_id"]})
        print(f"### Station {self.station_id} has spot available = {success} - spot_index = {spot_index}\n")

        self.last_ping = time.time()
        if not success:
            return

        spot = self.local_spots[spot_index][0]
        elapsed = time.time() - message["start_time"]
        self.local_spots[spot_index] = (spot, message["car_id"])
        print(f"%%% {self.station_id} lent spot {spot} to car {message['car_id']} in {elapsed:.4f} seconds | {message['in_need_station_id']} asked")
        print(f"%%% {self.station_id} spots: {self.local_spots}\n")

        self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
        response = self.manager_socket.recv_json()
                

    # Verifica se há um carro estacionado na estação
    # Se houver, sinaliza verdadeiro e retorna o índice da vaga
    # Se não houver, sinaliza falso e retorna None
    def look_for_car(self, car_id, start_time):

            while self.in_election:
                print(f"<<< Looking - Station {self.station_id} is in election")
                time.sleep(1)
                continue

            for spot_index, tuple in enumerate(self.local_spots):
                if tuple[1] == car_id:
                    self.local_spots[spot_index] = (self.local_spots[spot_index][0], None)
                    time_to_release = time.time() - start_time
                    print(f"\n*** {self.station_id} released spot {self.local_spots[spot_index][0]} from car {car_id} in {time_to_release:.4f} seconds")
                    print(f"*** {self.station_id} spots: {self.local_spots}")
                    self.manager_socket.send_json({"type": "update_station_spots", "station_id": self.station_id, "spots": self.local_spots, "status": 1})
                    response = self.manager_socket.recv_json()
                    return True
            return False


    # Busca pelo carro na fila de espera
    # Se encontrar remove e libera 
    def look_for_car_in_queue(self, car_id):
        while self.in_election:
            print(f"<<< Looking - Station {self.station_id} is in election")
            time.sleep(1)
            continue

        for i in range(global_car_queue.qsize()):
            if global_car_queue.queue[i] == car_id:
                global_car_queue.queue.remove(car_id)
                return True
        return False


    # Libera uma vaga de estacionamento
    # Broadcast para todas as estações para que elas busquem pelo carro e ja liberem a vaga
    def release_car(self, car_id):
        while self.in_election:
            print(f"<<< Releasing - Station {self.station_id} is in election")
            time.sleep(1)
            continue
        
        start = time.time()
        
        if self.look_for_car(car_id, start):
            print(f"$$$ Car {car_id} left on same station that entered {self.station_id}")

        elif self.look_for_car_in_queue(car_id):
            print(f"$$$ Car {car_id} left on queue in station {self.station_id} in {time.time() - start} seconds") 

        else:
            self.broadcast_socket.send_json({"type": "release_car", "leaving_station_id": self.station_id, "car_id": car_id, "start_time": start})


    ## Lida com requisições externas - simula a camada de APP do projeto
    ## AE - Ativar estação
    ## FE - Falha na estação
    ## VD - Vagas disponíveis em todas as estações
    ## RV - Requisitar vaga
    ## LV - Liberar vaga
    def handle_app_requests(self):
        poller = zmq.Poller()
        poller.register(self.app_socket, zmq.POLLIN)
        
        while True:
            socks = dict(poller.poll(timeout=1000))  # Verifica as sockets a cada 1 segundo

            # TENTATIVA PARA QUE A ESPERA PARA RESPONDER A MESNAGEM VD NAO TRAVE A CHEGADA DE OUTRAS MENSAGENS
            if self.app_socket in socks and socks[self.app_socket] == zmq.POLLIN:
                try:
                    if not self.app_socket.closed:
                        external_message = self.app_socket.recv(flags=zmq.NOBLOCK)
                        if external_message:
                            external_message = external_message.decode()
                            
                            ## Respondendo imediatamente AE, FE, RV, LV para nao travar a chegada de mensagens
                            if external_message != "VD":
                                self.app_socket.send_string("Received\n")
                                self.external_requests.put(external_message)

                            ## VD pode travar a socket enquanto busca pela lista de estações
                            ## Responde com a lista de estações ativas pro app
                            else:
                                print(f'(EXTERNAL) {external_message} in {self.station_id}\n')
                                if self.status == 0:
                                    self.app_socket.send(b"Station is inactive\n")
                                    continue
                                
                                self.manager_socket.send_json({"type": "request_format_active_stations"})
                                time.sleep(0.1)
                                try:
                                    response = self.manager_socket.recv_json(flags=zmq.NOBLOCK)
                                    print(f"\n(VD {self.station_id}) Active stations (ID, VagasTotais, VagasOcupadas, VagasVazias):")
                                    print(f"Active stations: {response['active_stations']}")
                                    self.app_socket.send(str(response["active_stations"]).encode())
                                
                                except zmq.Again as e:
                                    print("No response received from manager socket in non-blocking mode.")
                                    self.app_socket.send(b"No response received from manager.")
                    
                    else:
                        print(f"App socket closed in station {self.station_id}")
                        time.sleep(2)

                except zmq.Again:
                    time.sleep(0.2)
                    continue


    def process_app_requests(self):
        while True:
            if self.external_requests.empty():
                time.sleep(1)
                continue
            try:
                external_message = self.external_requests.get_nowait()
                print(f"\n(EXTERNAL) Received message: {external_message} in station {self.station_id}\n")
                
                if  external_message == "AE":
                    self.activate_station()

                elif external_message == "FE":
                    self.deactivate_station()
                
                elif external_message[0:2] == "RV":
                    if self.status == 0:
                        print(f"Station {self.station_id} is inactive")
                        continue
                    car_id = external_message[3:]
                    # print(f'\nRequisição de vaga em {self.station_id} = {car_id}')
                    self.allocate_spot(car_id)

                elif external_message[0:2] == "LV":
                    if self.status == 0:
                        print(f"Station {self.station_id} is inactive")
                        continue
                    car_id = external_message[3:]
                    # print(f'\nLiberar vaga em {self.station_id} = {car_id}')
                    self.release_car(car_id)

                    # time.sleep(1)
                else:
                    print(f"Invalid request: {external_message}")
            
            except Empty:
                time.sleep(1)
                continue
            

    # Lida com as requisições de outras estações e é uma thread separada
    # Requisições possíveis:
    # - request_spots: Requisição do número de vagas da estação, apenas responde com o número de vagas
    # - request_spots_list: Requisição da lista de vagas da estação, apenas responde com a lista de vagas
    # - update_spots: Atualização da lista de vagas da estação, apenas atualiza a lista de vagas
    # - ping: Requisição de ping, checa se a estação está ativa e responde com um ping_response
    # - ping_response: Resposta ao ping apenas para garantir a ordem da fila de respostas
    # - trigger_election: Disparo de eleição por mensagem de broadcast
    # - terminate_election: Terminar eleição por mensagem de broadcast
    # - reactivate_station: Teste para reativar a estação
    # - car_request_spot: Aloca de vaga da estação para um carro, apenas chama o método allocate_spot (ela entra pela estação que chama o metodo)
    # - car_borrow_spot:  Emprestimo de vaga em outra estaçao para um carro, se sucesso confirma com a estação requisitante
    # - release_car: Liberação de vaga, todas as estações buscam pelo carro mas apenas a que o encontrar o libera e informa ao manager
    
    def handle_requests(self):
        while True:
            try:
                if self.status == 0:
                    time.sleep(1)
                    continue

                if not self.subscriber_socket.closed:
                    message = self.subscriber_socket.recv_json(flags=zmq.NOBLOCK)
                    
                    if message:
                        # print(f"(INTERNAL {self.station_id}) Received message: ", message)
                        if message["type"] == "ping" and message["station_id"] != self.station_id:
                            # print(f"Received ping from {message['station_id']} in station {self.station_id}")
                            self.broadcast_socket.send_json({"type": "ping_response", "station_id": self.station_id, "ping_id": message["ping_id"], "target": message["station_id"]})
                
                        elif message["type"] == "ping_response" and message["target"] == self.station_id:
                            # DEBUG
                            # with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                            #     f.write(f"\n PING RESPONSE from {message['station_id']} in {self.station_id}\n")
                            self.ping_responses.put(message)
                    
                        else:
                            if message["type"] == "car_borrow_spot" and message["target_station_id"] != self.station_id:
                                continue
                            if message["type"] == "response_car_borrow_spot" and message["in_need_station_id"] != self.station_id:
                                continue
                            self.internal_requests.put(message)
                else:
                    print(f"Subscriber socket closed in station {self.station_id}")
                    time.sleep(2)

            except zmq.Again:
                time.sleep(0.2)
                continue


    def process_internal_requests(self):
        while True:  # Enquanto a estação estiver ativa
        
            if self.status == 0:    
                time.sleep(1)
                continue

            if self.internal_requests.empty():
                time.sleep(1)
                continue

            try:
                message = self.internal_requests.get_nowait()

                # DEBUG
                # with open("/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
                #     f.write(f"\nProcessando {message} em estação {self.station_id}\n")

                if message["type"] == "request_spots":
                    # print(f"Request spots from {message['station_id']} - received here {self.station_id} = {self.nspots}")
                    self.broadcast_socket.send_json({"type": "response_spots", "station_id": self.station_id, "nspots": self.nspots})
            
                elif message["type"] == "request_spots_list":
                    if message["target_station_id"] == self.station_id:
                        # print(f"ççç Request spots list from {message['station_id']} - received here {self.station_id} => list: {self.local_spots}")
                        self.broadcast_socket.send_json({"type": "response_spots_list", "station_id": self.station_id, "spots_list": self.local_spots})
                
                elif message["type"] == "update_spots":
                    if message["station_id"] == self.station_id: 
                        # print(f"Update spots received here {self.station_id} - list: {self.local_spots} x new list: {message['spots_list']}")
                        self.local_spots = message["spots_list"]
                        self.nspots = len(message["spots_list"])
                        # print(f":::: Station {self.station_id} updated spots: {self.local_spots} = len {self.nspots}")
                        self.broadcast_socket.send_json({"type": "response_update_spots", "station_id": self.station_id, "status": "success"})
                        # time.sleep(0.2)

                elif message["type"] == "update_connections":
                    # print(f"Updating connections {message['station_id']} - received here {self.station_id}")
                    # print(f"Old connections: {self.connections} x New connections: {message['connections']}")
                    self.connections = message["connections"]
                    self.last_ping = time.time()
                    # self.broadcast_socket.send_json({"type": "response_update_connections", "station_id": self.station_id, "status": "success"})

                elif message["type"] == "trigger_election":
                    self.in_election = True
                    if self.election_time == 0:
                        self.election_time = time.time()
                    
                    # print(f"\n;;; Received election trigger from {message['station_id']} in station {self.station_id} = {self.in_election}\n")
                    self.broadcast_socket.send_json({"type": "response_trigger_election", "station_id": self.station_id, "time": self.election_time})

                elif message["type"] == "terminate_election":
                    # print(f"Received election termination in station {self.station_id}")
                    self.in_election = False
                    self.election_time = 0
                    # self.election_proposals = {}
                    self.broadcast_socket.send_json({"type": "response_terminate_election", "station_id": self.station_id, "status": "success"})

                elif message["type"] == "car_request_spot" and message["station_id"] == self.station_id:
                    print(f"Received car request spot from {message['car_id']} in station {self.station_id}")
                    self.allocate_spot(message["car_id"])

                elif message["type"] == "car_borrow_spot" and message["target_station_id"] == self.station_id:
                    print(f"\n+++> REQUEST car borrow spot from {message['in_need_station_id']} here in station {self.station_id} = car {message['car_id']}")
                    self.executor.submit(self.borrow_spot, message)

                elif message["type"] == "response_car_borrow_spot" and message["in_need_station_id"] == self.station_id:
                    print(f"<+++ RESPONSE car borrow spot from {message['station_id']} here in station {self.station_id} = {message['status']}\n")
                    self.current_car = message["car_id"]
                    self.current_station_borrowing = message["station_id"]
                    self.current_status_borrowing = message["status"]

                elif message["type"] == "release_car":
                    print(f"\n--- Received release car from {message['car_id']} in station {self.station_id}")
                    self.executor.submit(self.look_for_car, message["car_id"], message["start_time"])

            except Empty:
                time.sleep(1)
                continue


    def clean_up(self):
        self.broadcast_socket.close()
        self.subscriber_socket.close()
        self.manager_socket.close()
        self.app_socket.close()
        self.context.term()


    def run(self):
        print(f"Station {self.station_id} is active but hibernating in {self.port}")
        self.last_ping = time.time()
        external_thread = threading.Thread(target=self.handle_app_requests)
        external_thread.daemon = True
        external_thread.start()

        process_thread = threading.Thread(target=self.process_app_requests)
        process_thread.daemon = True
        process_thread.start()

        request_thread = threading.Thread(target=self.handle_requests)
        request_thread.daemon = True
        request_thread.start()

        process_internal_thread = threading.Thread(target=self.process_internal_requests)
        process_internal_thread.daemon = True
        process_internal_thread.start()
        
        ping_thread = threading.Thread(target=self.ping)
        ping_thread.daemon = True
        ping_thread.start()
    

if __name__ == "__main__":

    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path, "..")
    stations_file = os.path.join(path, STATIONS_FILE)
    stations = []
    with open(stations_file, "r") as file:
        for line in file:
            station_id, ipaddr, port = line.strip().split(" ")
            stations.append((station_id, ipaddr, int(port)+1))

    station_id = sys.argv[1]
    ipaddr = sys.argv[2]
    port = int(sys.argv[3])
    other_stations = [(s[1], s[2]) for s in stations if s[0] != station_id]
    print(f"Station {station_id} - IP: {ipaddr} - Port: {port}\nOther stations: {other_stations}\n \t-----------\n")
    
    s = Station(
        station_id=station_id,
        ipaddr=ipaddr,
        port=port,
        manager_ip=manager_ip,
        manager_port=manager_port,
        other_stations=other_stations
    )
    s.run()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        # s.clean_up()
