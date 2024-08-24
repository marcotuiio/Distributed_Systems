import threading
import zmq
from manager import Manager

class StationMiddleware:
    def __init__(self, station_id, ipaddr, port, manager):
        self.station_id = station_id
        self.ipaddr = ipaddr
        self.port = port
        self.status = 0
        self.manager = manager

        self.nspots = 0
        self.local_spots = {}

        # Dicionario que guarda as conexões com as outras estações via BROADCAST
        self.connections = {} 

        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.REP)
        self.sock.bind(f"tcp://{self.ipaddr}:{self.port}")


    def run(self):
        print(f"Estação {self.station_id} iniciada.")
        while True:
            message = self.sock.recv_string()
            print(f"Estação {self.station_id} recebeu: {message}")
            # Lógica para processar mensagens (ex: alocação de vagas)
            self.sock.send_string(f"A estação {self.station_id} processou a mensagem.")


    def activate_station(self):
        self.status = 1
        self.manager.activate_station(self.station_id)
        


    def deactivate_station(self):
        self.status = 0
        self.manager.deactivate_station(self.station_id)


    def print_station_spots(self):
        print(f"Estação {self.station_id} tem {self.nspots} vagas.")
        print(f"Vagas: {self.local_spots}")
    

    def allocate_spot(self):
        if self.spots > 0:
            self.spots -= 1
            print(f"Carro estacionado na estação {self.station_id}. Vagas restantes: {self.spots}")
        else:
            print(f"Estação {self.station_id} sem vagas disponíveis.")
            # Lógica para solicitar vagas de outras estações via middleware.
