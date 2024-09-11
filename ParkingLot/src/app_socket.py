# from manager import Manager
import threading
import socket

class App:
    def __init__(self, ip, port, station):
        self.external_ip = ip
        self.external_port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.external_ip, self.external_port))
        self.station = station


    def run(self):
        self.socket.listen(1)
        print(f"Listening on {self.external_ip}:{self.external_port}")

        while True:
            connection, client_address = self.socket.accept()
            try:
                print(f"Connection from {client_address}")

                # Receive the data in small chunks and retransmit it
                while True:
                    data = connection.recv(1024)
                    if data:
                        data = data.decode()    
                        if data == "AE":
                            response = self.station.activate_station()
                            connection.sendall(response.encode())
                        # Send a response back to the client
                    else:
                        break
            finally:
                connection.close()



