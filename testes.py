# import pandas as pd

# users = [
#     {
#         "user": "robert@gmail",
#         "password": "1234",
#         "cookies": "0999"
#     },
#     {
#         "user": "dany@west",
#         "password": "9098",
#         "cookies": "0114"
#     }
# ]

# pedidos = [
#     {
#         "session":"abc345",
#         "id": "98hb",
#         "livros": [
#             "1984",
#             "Moby Dick"
#         ],
#         "preco": 75,
#     },
#     {
#         "session":"abc345",
#         "id": "msax2",
#         "livros": [
#             "O Senhor dos Anéis - Edição Especial"
#         ],
#         "preco": 200,
#     }
# ]

# # login = "robert@gmail"
# # df = pd.DataFrame(users)
# # # print(df["user"].tolist())

# # # if login in df["user"].tolist():
# # matching_row = df.loc[df["user"] == login]
# # print(matching_row["password"].iloc[0])
# # if not matching_row.empty:
# #     print("its here!!")
# # else:
# #     print(f"no user with this login <{login}>")

# # print(df["user"].iloc[0])
# session = "abc345"
# matching_pedidos = [pedido for pedido in pedidos if pedido["session"] == session]

# # print(f'matching {matching_pedidos}')
# all_livros = []
# for pedido in matching_pedidos:
#     for titulos in pedido["livros"]:
#         all_livros.append(titulos)
#     # print(f'titulos {titulos}')
#     # livros = [gestao_pb2.IdLivro(titulo=livro["titulo"]) for livro in pedido["livros"]]
#     # all_livros.extend(livros)
# print(all_livros)

# total_slots = 100  # Example total slots
# empty_slots = [i for i in range(total_slots)]

# print(empty_slots)

# total = 10
# station_id = 5
# spot = {}

# spots = {i: station_id for i in range(total)}

# print(spots)

# # test_list = list(spots.keys())
# # print(test_list)

# spots_station5 = [spot for spot, station in spots.items() if station == station_id]
# print(spots_station5)

# stations = {
#     0: {"name": "Station A", "id": 0, "nspots": 5},
#     1: {"name": "Station B", "id": 1, "nspots": 1},
#     2: {"name": "Station C", "id": 2, "nspots": 10},
#     3: {"name": "Station D", "id": 3, "nspots": 7},
# }

# max_station_id = max(stations, key=lambda x: stations[x]["nspots"])
# print(f"Estação com o maior número de vagas: {max_station_id}")

# stations = ['Station A', 'Station B', 'Station C', 'Station D']
# response = ['Station A', 'Station C']

# print(set(stations) - set(response) - set(['Station D']))

# spots = [('Station A', None), ('Station B', 1), ('Station C', 2), ('Station D', 3)]

# for i, tup in enumerate(spots):
#     if tup[1] is None:
#         print(i, tup)
#         break


### Comunicações via socket TCP simples como originalmente no codigo

# import socket

# server_ip = '127.0.0.1'
# server_port = 5555

# # Create a TCP/IP socket
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.bind((server_ip, server_port))
# sock.listen(1)

# print(f"Listening on {server_ip}:{server_port}")

# while True:
#     connection, client_address = sock.accept()
#     try:
#         print(f"Connection from {client_address}")

#         # Receive the data in small chunks and retransmit it
#         while True:
#             data = connection.recv(1024)
#             if data:
#                 print(f"Received: {data.decode()}")
#                 # Send a response back to the client
#                 connection.sendall(b"Message received")
#             else:
#                 break
#     finally:
#         connection.close()


### Testando zmq + json com codigo do sakuray -> tem mais algumas facilidade e abstrações uteis

# import zmq
# import time
# import json

# context = zmq.Context()
# socket = context.socket(zmq.REP)
# socket.bind("tcp://localhost:5555")

# while True:
#     try:
#         response = socket.recv(flags=zmq.NOBLOCK)
#         if not response:
#             print("Received empty message")
#             continue
        
#         decoded = response.decode('utf-8')
#         print(f"Recebi da Estação de Controle {response} x {decoded}")

#         message = json.loads(response.decode('utf-8'))
#         print(f"Decoded JSON message: {message}")

#         # Send a reply
#         socket.send_string("Message received from Manager")
#         time.sleep(1)
#     except zmq.Again:
#         print("No response")
#         time.sleep(1)
#         continue
#     except json.JSONDecodeError as e:
#         print(f"JSON decode error: {e}")
#         continue


# vagas = [1]
# half = len(vagas) // 2
# vags2 = vagas[half:]
# vags3 = vagas[:half]

# print(vags2)
# print(vags3)

stations ={ 
            "Station0": {"id": "Station0", "ipaddr": "127.0.0.1", "port": 5000, "status": 1, "spots": [(13, 'carro3'), (14, 'carro5')]},
            "Station1": {"id": "Station1", "ipaddr": "127.0.0.1", "port": 5010, "status": 1, "spots": [(12, None), (10, 'carro1'), (11, 'carro2')]}
        }

# for spots in stations["Station0"]["spots"]:
#     print(spots)
# stations["Station0"]["spots"] = []
# for spots in stations["Station0"]["spots"]:
#     print(spots)

# active_stations = []
# for station in stations:
#     if stations[station]["status"] == 1:
#         ocupadas = len([spot for spot in stations[station]["spots"] if spot[1] is not None])
#         total = len(stations[station]["spots"])
#         vazias = total - ocupadas
#         active_stations.append((station, total, ocupadas, vazias))
# print(active_stations)

# message = "RV.ohxwys"

# print(message[3:])
# print(message[0:2])