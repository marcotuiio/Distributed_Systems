import pandas as pd
import streamlit as st 

import grpc
import catalogo.catalogo_pb2 as catalogo_pb2
import catalogo.catalogo_pb2_grpc as catalogo_pb2_grpc

import auth.auth_pb2 as auth_pb2
import auth.auth_pb2_grpc as auth_pb2_grpc


def login(stub):

    st.title('Login na BookStore do DC')
    login_email = st.text_input("Email")
    login_senha = st.text_input("Password", type="password")

    if st.button("Login"):
        response = stub.LoginUser(auth_pb2.UserData(login_email=login_email, login_senha=login_senha))
        if response.response:
            st.session_state.session_cookie = response.session_cookie
            st.session_state.logged_in = True
            st.success("Login com sucesso!")
        else:
            st.error(response.message)

    if st.button("Criar Conta"):
        response = stub.CreateUser(auth_pb2.UserData(login_email=login_email, login_senha=login_senha))
        if response.response:
            st.session_state.session_cookie = response.session_cookie
            st.session_state.logged_in = True
            st.success("Conta criada com sucesso!")
        else:
            st.error(response.message)

def catalog(stub):

    # Inicializar a lista de livros selecionados
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    # Configurar o título da aplicação
    st.title('BookStore do DC')

    # if st.button("Exibir catálogo", type="primary"):
    st.write("Selecione os livros que deseja adicionar ao carrinho:")

    # Preparando para fazer request dos livros ao servidor
    session = catalogo_pb2.Session(session_cookie=st.session_state.session_cookie)
    response = stub.GetCatalogo(session)
    print("\n* ShowCatalogo Response Received")

    # Convertendo o formato da response para um dataframe do pandas
    books = [
        {
            "Carrinho": book.carrinho,
            "Título": book.titulo,
            "Autor": book.autor,
            "Publicação": book.publicacao,
            "Em Estoque": book.em_estoque,
            "Preço (R$)": book.preco,
            "Descrição": book.descricao
        }
        for book in response.books
    ]
    df = pd.DataFrame(books)

    # Adicionar checkboxes na tabela
    edited_df = st.data_editor(df)

    # Adicionar livros selecionados ao carrinho
    if st.button("Confirmar Compra"):
        selected_books = [
            catalogo_pb2.IdLivro(titulo=book['Título'])
            for i, book in edited_df.iterrows() if book['Carrinho']
        ]

        st.session_state.carrinho.extend(selected_books)
        # print(selected_books)

        # Preparando para fazer request da compra ao servidor
        list_carrinho = catalogo_pb2.ListCarrinho(livros_carrinho=selected_books)
        response = stub.UpdateCatalogo(list_carrinho)

        # st.markdown(f"```\n{response.m}\n```")
        st.success(response.m)
        print("\n* ShowCatalogo Response Received")

    if st.button("SAIR", type="primary"):
        st.session_state.session_cookie = ""
        st.session_state.logged_in = False


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        auth_stub = auth_pb2_grpc.UserAuthStub(channel)
        catalog_stub = catalogo_pb2_grpc.ShowCatalogoStub(channel)

        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login(auth_stub)
        else:
            catalog(catalog_stub)


if __name__ == "__main__":
    run()