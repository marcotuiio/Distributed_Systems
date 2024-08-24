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

total = 10
station_id = 5
spot = {}

spots = {i: station_id for i in range(total)}

print(spots)

# test_list = list(spots.keys())
# print(test_list)

spots_station5 = [spot for spot, station in spots.items() if station == station_id]
print(spots_station5)

# stations = {
#     0: {"name": "Station A", "id": 0, "nspots": 5},
#     1: {"name": "Station B", "id": 1, "nspots": 1},
#     2: {"name": "Station C", "id": 2, "nspots": 10},
#     3: {"name": "Station D", "id": 3, "nspots": 7},
# }

# max_station_id = max(stations, key=lambda x: stations[x]["nspots"])
# print(f"Estação com o maior número de vagas: {max_station_id}")