from concurrent import futures
import grpc
import catalogo.catalogo_pb2 as catalogo_pb2
import catalogo.catalogo_pb2_grpc as catalogo_pb2_grpc


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

        reply = catalogo_pb2.FullCatalogo(books=self.books)

        return reply
    
    def UpdateCatalogo(self, request, context):
        print("+ UpdateCatalogo Request Made:")
        message = ""

        titulos = [no_carrinho.titulo for no_carrinho in request.livros_carrinho]
        # print(titulos)

        for b in self.books:
            if b.titulo in titulos:
                if b.em_estoque > 0:
                    b.em_estoque -= 1;
                    message += f"{b.titulo} comprado com sucesso! :D \t\t"
                else:
                    message += f"{b.titulo} sem estoque. :D \t\t"

        message += f"Operação concluída! :D \t\t"
        # print(message)
        return catalogo_pb2.SuccessMessage(m=message)
    

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    catalogo_pb2_grpc.add_ShowCatalogoServicer_to_server(ShowCatalogoServicer(), server)
    server.add_insecure_port("localhost:50051")
    server.start()
    print("DC's BookStore Server is up and running")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()