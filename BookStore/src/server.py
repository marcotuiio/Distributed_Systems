from concurrent import futures
import pandas as pd
import random
import string
import grpc

import catalogo.catalogo_pb2 as catalogo_pb2
import catalogo.catalogo_pb2_grpc as catalogo_pb2_grpc

import auth.auth_pb2 as auth_pb2
import auth.auth_pb2_grpc as auth_pb2_grpc


class UserAuthServicer(auth_pb2_grpc.UserAuthServicer):
    def __init__(self):
        self.users = [
            {
                "user": "robert@gmail",
                "password": "1234",
                "cookies": "0999"
            }
        ]

    def CreateUser(self, request, context):
        df = pd.DataFrame(self.users)
        matching_row = df.loc[df["user"] == request.login_email]

        # Verifica existencia do email e se possivel cria um novo usuario com os valores recebidos do request
        if not matching_row.empty:
            return auth_pb2.LoginResponse(response=False, session_cookie=None, message="Esse usuário já existe, tente novamente.")
        else:
            cookie = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            new_user = {"user": request.login_email, "password": request.login_senha, "cookies": cookie}
            print(f'\nUsuario {request.login_email} criado {request.login_senha} | {cookie}\n')
            self.users.append(new_user)
            return auth_pb2.LoginResponse(response=True, session_cookie=cookie, message="Usuário criado com sucesso.")
        
    def LoginUser(self, request, context):
        df = pd.DataFrame(self.users)
        matching_row = df.loc[df["user"] == request.login_email]
        
        # Verifica existencia e se possivel verifica se as credenciais estao corretas, para enfim liberar o cookie e acesso ao catalogo
        if matching_row.empty:
            return auth_pb2.LoginResponse(response=False, session_cookie=None, message="Usuário não encontrado, tente novamente.")
        else:
            if matching_row["password"].iloc[0] == request.login_senha:
                print(f'\nUsuario {matching_row["user"].iloc[0]} logando {matching_row["password"].iloc[0]} | {matching_row["cookies"].iloc[0]}\n')
                return auth_pb2.LoginResponse(response=True, session_cookie=matching_row["cookies"].iloc[0], message="Login bem-sucedido.")
            else:
                return auth_pb2.LoginResponse(response=False, session_cookie=None, message="Credenciais incorretas, tente novamente.")        

class ShowCatalogoServicer(catalogo_pb2_grpc.ShowCatalogoServicer):

    def __init__(self):
        self.books = [
            catalogo_pb2.Book(
                carrinho=False,
                titulo="O Senhor dos Anéis - Edição Especial",
                autor="J.R.R. Tolkien",
                publicacao=1954,
                em_estoque=25,
                preco=200,
                descricao="Uma saga épica de fantasia sobre a luta contra o mal na Terra Média."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="1984",
                autor="George Orwell",
                publicacao=1949,
                em_estoque=10,
                preco=30,
                descricao="Uma distopia que explora os perigos do totalitarismo e da vigilância extrema."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="Cem Anos de Solidão",
                autor="Gabriel García Márquez",
                publicacao=1967,
                em_estoque=5,
                preco=70,
                descricao="A saga da família Buendía, marcada por gerações de solidão e eventos extraordinários."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="O Apanhador no Campo de Centeio",
                autor="J.D. Salinger",
                publicacao=1951,
                em_estoque=5,
                preco=65,
                descricao="A jornada de Holden Caulfield, um adolescente enfrentando a angústia e a alienação."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="Orgulho e Preconceito",
                autor="Jane Austen",
                publicacao=1813,
                em_estoque=20,
                preco=25,
                descricao="Uma comédia de costumes que examina as questões de classe, família e romance na Inglaterra do século XIX."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="Moby Dick",
                autor="Herman Melville",
                publicacao=1851,
                em_estoque=1,
                preco=35,
                descricao="A épica aventura do capitão Ahab em busca da vingança contra a baleia branca, Moby Dick."
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="The World of Ice and Fire",
                autor="George R R Martin",
                publicacao=2014,
                em_estoque=20,
                preco=150,
                descricao="É um livro compêndio sobre o universo da série de fantasia épica que inspirou Game of Thrones"
            ),
            catalogo_pb2.Book(
                carrinho=False,
                titulo="Bíblia Sagrada",
                autor="-",
                publicacao=2024,
                em_estoque=100,
                preco=40,
                descricao="A Bíblia é uma antologia de textos religiosos ou escrituras sagradas para o cristianismo e muitas outras religiões"
            )
        ]

    def GetCatalogo(self, request, context):
        print("+ GetCatalogo Request Made:")
        print(request)

        # Como na interface foi definido que esse metodo deve passar livros, no formato especificado, repetidas vezes
        # aqui é feito esse preparo e envio de resposta ao client
        reply = catalogo_pb2.FullCatalogo(books=self.books)

        return reply
    
    def UpdateCatalogo(self, request, context):
        print("+ UpdateCatalogo Request Made:")
        message = ""

        # Pegando apenas o canto de valor, descartando a chave, para agilizar a busca posterior
        titulos = [no_carrinho.titulo for no_carrinho in request.livros_carrinho]
        # print(titulos)

        # Percorre a lista completa de livros, verificando se aquele livro esta presente no carrinho
        # caso esteja e tenha estoque, faz o necessario e retorna a mensagem com os resultados de cada um
        for b in self.books:
            if b.titulo in titulos:
                if b.em_estoque > 0:
                    b.em_estoque -= 1;
                    message += f"{b.titulo} comprado com sucesso! :D \t\t"
                else:
                    message += f"{b.titulo} sem estoque. :D \t\t"

        message += f"Operação concluída! :D \t\t"
        # print(message)
        
        ######## GERAR E RETORNAR PEDIDO

        return catalogo_pb2.SuccessMessage(m=message)
    

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_UserAuthServicer_to_server(UserAuthServicer(), server)
    catalogo_pb2_grpc.add_ShowCatalogoServicer_to_server(ShowCatalogoServicer(), server)
    server.add_insecure_port('localhost:50051')
    server.start()
    print("DC's BookStore Server is up and running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()