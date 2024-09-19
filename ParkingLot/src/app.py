import zmq
import threading
import time
import os
import sys
from queue import Queue, Empty


class AppSocket:
    def __init__(self, station_id, ipaddr, port):
        self.station_id = station_id
        
        # Requisições externas do Controle .cpp
        self.app_socket = zmq.Context().socket(zmq.REP)
        self.app_socket.bind(f"tcp://{self.ipaddr}:{self.port-1}")
        
        # Encaminhar requisições para o Middleware
        self.middleware_socket = zmq.Context().socket(zmq.REQ)
        self.middleware_socket(f"tcp://{self.ipaddr}:{self.port-2}")

        # Fila de mensagens
        self.message_queue = Queue()


    ## Lida com requisições externas - simula a camada de APP do projeto
    ## AE - Ativar estação
    ## FE - Falha na estação
    ## VD - Vagas disponíveis em todas as estações
    ## RV - Requisitar vaga
    ## LV - Liberar vaga
    def handle_app_requests(self):
        while True:
            try:
                message = self.app_socket.recv(flags=zmq.NOBLOCK)
                if message:
                    message = message.decode()
                    self.app_socket.send(b"Message received\n")

                    self.message_queue.put(message)
                    external_message = self.message_queue.get()

                    print(f"(EXTERNAL) Received message: {external_message} in station {self.station_id}")
                    self.middleware_socket.send_string(external_message)

                    middleware_response = self.middleware_socket.recv_string()
                    print(f"(EXTERNAL) Middleware response: {middleware_response} in station {self.station_id}")
                    # self.app_socket.send_string(middleware_response)
                else:
                    time.sleep(1)
                    continue

            except zmq.Again:
                time.sleep(1)
                continue


if __name__ == "__main__":
    station_id = sys.argv[1]
    ipaddr = sys.argv[2]
    port = int(sys.argv[3])

    app_socket = AppSocket(station_id, ipaddr, port)
    
    app_thread = threading.Thread(target=app_socket.handle_app_requests)
    app_thread.start()
    app_thread.join()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Closing app socket")
        # app_socket.app_socket.close()
        # app_socket.middleware_socket.close()
