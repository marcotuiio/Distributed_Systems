import zmq
import threading
import time
import os

STATIONS_FILE = "stations.txt"
TOTAL_SPOTS = 10

manager_ip = "127.0.0.1"
manager_port = 5555

class Manager:
    def __init__(self, total_spots):
        self.total_spots = total_spots
        # self.lock = threading.Lock()
        self.stations = {
            "Station0": {"id": "Station0", "ipaddr": "127.0.0.1", "port": 5000, "status": 0, "spots": []},
            "Station1": {"id": "Station1", "ipaddr": "127.0.0.1", "port": 5010, "status": 0, "spots": []},
            "Station2": {"id": "Station2", "ipaddr": "127.0.0.1", "port": 5020, "status": 0, "spots": []},
            "Station3": {"id": "Station3", "ipaddr": "127.0.0.1", "port": 5030, "status": 0, "spots": []},
            "Station4": {"id": "Station4", "ipaddr": "127.0.0.1", "port": 5040, "status": 0, "spots": []},
            "Station5": {"id": "Station5", "ipaddr": "127.0.0.1", "port": 5050, "status": 0, "spots": []},
            "Station6": {"id": "Station6", "ipaddr": "127.0.0.1", "port": 5060, "status": 0, "spots": []},
            "Station7": {"id": "Station7", "ipaddr": "127.0.0.1", "port": 5070, "status": 0, "spots": []},
            "Station8": {"id": "Station8", "ipaddr": "127.0.0.1", "port": 5080, "status": 0, "spots": []},
            "Station9": {"id": "Station9", "ipaddr": "127.0.0.1", "port": 5090, "status": 0, "spots": []}
        }
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{manager_ip}:{manager_port}")

        self.active_stations = []

    # Escreve as informações das estações no arquivo file.txt
    def print_stations_to_file(self):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        stations_path = os.path.join(path, STATIONS_FILE)
        with open(stations_path, "w") as f:
            for station_id, station in self.stations.items():
                # print(f"{station['id']} {station['ipaddr']} {station['port']}")
                f.write(f"{station['id']} {station['ipaddr']} {station['port']}\n")


    # DEBUG: Printa as estações e suas vagas e o id das estações ativas
    def print_stations(self):
        print("\n")
        for station_id, station in self.stations.items():
            station_spots = [spot for spot in station["spots"]]
            print(f"Estação {station_id}: {station_spots}")
        print(f'\nEstações ativas: {self.active_stations}')

    # DEBUG: Retorna a estação com o id passado
    def get_station(self, station_id):
        return self.stations[station_id]


    # Lida com as requisições que envolvem o manager
    # Requisições possíveis:
    # - request_active_stations: Requisição das estações ativas
    # - request_total_spots: Requisição do número total de vagas
    # - update_station_spots: Atualiza vagas de uma estação
    def manager_handle_requests(self):
        while True:
            try:
                message = self.socket.recv_json(flags=zmq.NOBLOCK)
                print(f">>> Received message: {message}")
                if message["type"] == "request_active_stations":
                    # with self.lock:
                    self.socket.send_json({"type": "response_active_stations", "active_stations": self.active_stations})

                elif message["type"] == "request_total_spots":
                    self.socket.send_json({"type": "response_total_spots", "total_spots": self.total_spots})
                
                elif message["type"] == "update_station_spots":
                    station_id = message["station_id"]
                    spots = message["spots"]

                    if message["status"] == 1:
                        if self.active_stations.count(station_id) == 0:
                            self.active_stations.append(station_id)
                        self.stations[station_id]["status"] = 1
                    elif message["status"] == 0:
                        if self.active_stations.count(station_id) > 0:
                            self.active_stations.remove(station_id)
                            self.stations[station_id]["status"] = 0

                    self.stations[station_id]["spots"] = spots
                    self.socket.send_json({"type": "response_update_station_spots", "status": "success", "active_stations": self.active_stations})

                elif message["type"] == "request_spots_from_station":
                    station_id = message["station_id"]
                    spots = self.stations[station_id]["spots"]
                    self.socket.send_json({"type": "response_spots_from_station", "spots": spots})
                    # Deixar os spots de quem cedeu vazios para nao duplicar a vaga
                    self.stations[station_id]["spots"] = []
                        

                elif message["type"] == "request_format_active_stations":
                    active_stations = []
                    for station in self.stations:
                        if self.stations[station]["status"] == 1:
                            ocupadas = len([spot for spot in self.stations[station]["spots"] if spot[1] is not None])
                            total = len(self.stations[station]["spots"])
                            vazias = total - ocupadas
                            active_stations.append((station, total, ocupadas, vazias))
                            
                    self.socket.send_json({"type": "response_format_active_stations", "active_stations": active_stations})

                elif message["type"] == "print_stations":
                    self.print_stations()
                    self.socket.send_json({"type": "response_print_stations", "status": "success"})
                
                elif message["type"] == "test_connection":
                    print("Connection test successful")
                    self.socket.send_json({"type": "response_test_connection", "status": "success"})

            except zmq.Again:
                time.sleep(0.1)


    def run(self):
        print("Manager is running...\n")
        self.manager_handle_requests()
        while True:
            pass
        

if __name__ == "__main__":
    manager = Manager(total_spots=TOTAL_SPOTS)
    manager_thread = threading.Thread(target=manager.run)
    manager_thread.start()

    manager.print_stations_to_file()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        # manager_thread.join()
        print("Manager exited successfully")
