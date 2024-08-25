import zmq
import threading
import time
from queue import Queue, Empty
import uuid

####### TRAPACEANDO - Nao estou conseguind travar a eleição nas multiplas threads
####### Detectar a eleiçõ funciona bem, o problema esta sendo tratar da eleição, pois
####### todas as estações estão tentando tratar a eleição ao mesmo tempo e ai as portas
####### estao sobrecarregadas e o sistema quebra e nenhuma eleição é feita
####### Entao vou criar um lock global para todas as estações e tentar fazer a eleição

GLOBAL_LOCK_IN_ELECTION = threading.Lock()

RESPONSE_TIMEOUT = 5
PING_INTERVAL = 10
PING_RETRY = 3

class Station:
    def __init__(self, station_id, ipaddr, port, manager_ip, manager_port, other_stations=[]):
        self.station_id = station_id
        self.ipaddr = ipaddr
        self.port = port
        self.status = 0
        self.last_ping = time.time()

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


    # Lida com as requisições de outras estações e é uma thread separada
    # Requisições possíveis:
    # - request_spots: Requisição do número de vagas da estação
    # - request_spots_list: Requisição da lista de vagas da estação
    # - update_spots: Atualização da lista de vagas da estação
    # - ping: Requisição de ping
    # - ping_response: Resposta ao ping apenas para garantir a ordem da fila de respostas
    # - trigger_election: Disparo de eleição nao esta sendo usada mas é uma mensagem de broadcast
    # - terminate_election: Terminar eleição nao esta sendo usada mas é uma mensagem de broadcast
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
                        # print(f"Update spots received here {self.station_id}")
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

            except zmq.Again:
                time.sleep(0.1) # Descanso para não sobrecarregar o processador


    def run(self):
        self.activate_station()
        request_thread = threading.Thread(target=self.handle_requests)
        request_thread.start()

        ping_thread = threading.Thread(target=self.ping)
        ping_thread.start()

        return request_thread, ping_thread


if __name__ == "__main__":
    t = []
    station1 = Station(station_id="Station1", ipaddr="127.0.0.3", port=5010, manager_ip="127.0.0.3", manager_port=5555, 
                   other_stations=[("127.0.0.3", 5020), ("127.0.0.3", 5030), ("127.0.0.3", 5040)])
    t1, t2 = station1.run()
    
    time.sleep(3)

    station2 = Station(station_id="Station2", ipaddr="127.0.0.3", port=5020, manager_ip="127.0.0.3", manager_port=5555,
                       other_stations=[("127.0.0.3", 5010), ("127.0.0.3", 5030), ("127.0.0.3", 5040)])
    t3, t4 = station2.run()
    
    time.sleep(3)

    station3 = Station(station_id="Station3", ipaddr="127.0.0.3", port=5030, manager_ip="127.0.0.3", manager_port=5555,
                       other_stations=[("127.0.0.3", 5020), ("127.0.0.3", 5010), ("127.0.0.3", 5040)])
    t5, t6 = station3.run()

    time.sleep(3)

    station4 = Station(station_id="Station4", ipaddr="127.0.0.3", port=5040, manager_ip="127.0.0.3", manager_port=5555,
                       other_stations=[("127.0.0.3", 5020), ("127.0.0.3", 5010), ("127.0.0.3", 5030)])  
    t7, t8 = station4.run()

    # t.extend([t1, t2, t3, t4, t5, t6, t7, t8])
    # for thread in t:
    #     thread.join()


    # time.sleep(5)
    # print(f'\nStation1: {station1.local_spots}')
    # print(f'Station2: {station2.local_spots}')
    # print(f'Station3: {station3.local_spots}')
    # print(f'Station4: {station4.local_spots}\n')
    
    time.sleep(4)
    station1.deactivate_station()

    # time.sleep(5)
    # print(f'\nStation1: {station1.local_spots}')
    # print(f'Station2: {station2.local_spots}')
    # print(f'Station3: {station3.local_spots}')
    # print(f'Station4: {station4.local_spots}')
