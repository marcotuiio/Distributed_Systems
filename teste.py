import pandas as pd

users = [
    {
        "user": "robert@gmail",
        "password": "1234",
        "cookies": "0999"
    },
    {
        "user": "dany@west",
        "password": "9098",
        "cookies": "0114"
    }
]

pedidos = [
    {
        "session":"abc345",
        "id": "98hb",
        "livros": [
            "1984",
            "Moby Dick"
        ],
        "preco": 75,
    },
    {
        "session":"abc345",
        "id": "msax2",
        "livros": [
            "O Senhor dos Anéis - Edição Especial"
        ],
        "preco": 200,
    }
]

# login = "robert@gmail"
# df = pd.DataFrame(users)
# # print(df["user"].tolist())

# # if login in df["user"].tolist():
# matching_row = df.loc[df["user"] == login]
# print(matching_row["password"].iloc[0])
# if not matching_row.empty:
#     print("its here!!")
# else:
#     print(f"no user with this login <{login}>")

# print(df["user"].iloc[0])
session = "abc345"
matching_pedidos = [pedido for pedido in pedidos if pedido["session"] == session]

# print(f'matching {matching_pedidos}')
all_livros = []
for pedido in matching_pedidos:
    for titulos in pedido["livros"]:
        all_livros.append(titulos)
    # print(f'titulos {titulos}')
    # livros = [gestao_pb2.IdLivro(titulo=livro["titulo"]) for livro in pedido["livros"]]
    # all_livros.extend(livros)
print(all_livros)