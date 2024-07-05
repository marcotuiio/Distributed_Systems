import pandas as pd
import streamlit as st
import grpc

import catalogo.catalogo_pb2 as catalogo_pb2
import catalogo.catalogo_pb2_grpc as catalogo_pb2_grpc

import auth.auth_pb2 as auth_pb2
import auth.auth_pb2_grpc as auth_pb2_grpc

import gestao.gestao_pb2 as gestao_pb2
import gestao.gestao_pb2_grpc as gestao_pb2_grpc


def login(stub):
    st.title('Login na BookStore do DC')
    
    with st.form(key='login_form'):
        login_email = st.text_input("Email")
        login_senha = st.text_input("Senha", type="password")
        login_button = st.form_submit_button("Login")
        create_account_button = st.form_submit_button("Criar Conta")
    
    ## Ambas as operacoes de autenticacao retornam uma string de cookie para identificar a session
    ## É a tentativa de implementar uma aunteticacao e sessao por user

    if login_button:
        # Preparando e enviando requisao de login com dados preenchidos no form
        response = stub.LoginUser(auth_pb2.UserData(login_email=login_email, login_senha=login_senha))
        if response.response:
            st.session_state.session_cookie = response.session_cookie
            st.session_state.logged_in = True
            st.success("Login com sucesso!")
            st.rerun()  
        else:
            st.error(response.message)
    
    if create_account_button:
        # # Preparando e enviando requisao de criar conta com dados preenchidos no form
        response = stub.CreateUser(auth_pb2.UserData(login_email=login_email, login_senha=login_senha))
        if response.response:
            st.session_state.session_cookie = response.session_cookie
            st.session_state.logged_in = True
            st.success("Conta criada com sucesso!")
            st.rerun()  # To rerun the script and show the catalog
        else:
            st.error(response.message)

def catalog(stub, gestao_stub):
    # Inicializar a lista de livros selecionados
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    st.title('BookStore do DC')
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

    # Adicionar livros selecionados ao carrinho e confirmar remove direto do estoque
    if st.button("Confirmar Compra"):
        # Montando uma lista dos titulos selecionados e passando a mesma para o request
        # Na interface foi definido que esse request deve receber repetidas strings, ou seja, uma lista de titulos
        selected_books = [
            catalogo_pb2.IdLivro(titulo=book['Título'])
            for i, book in edited_df.iterrows() if book['Carrinho']
        ]
        st.session_state.carrinho.extend(selected_books)
        list_carrinho = catalogo_pb2.ListCarrinho(livros_carrinho=selected_books)
        response = stub.UpdateCatalogo(list_carrinho)
        st.success(response.m)
        print("\n* ShowCatalogo Response Received")

    consultar_pedido(gestao_stub)

    # Remove o cookie da session e atualiza a pagina
    if st.button("SAIR", type="primary"):
        st.session_state.session_cookie = ""
        st.session_state.logged_in = False
        st.rerun()

def consultar_pedido(stub):
    with st.form(key='consultar_pedido'):
        id_form = st.text_input("ID Pedido")
        consultar_button = st.form_submit_button("Consultar Pedido")

    if consultar_button:
        # Preparando e enviando requisao de login com dados preenchidos no form
        response = stub.ConsultarPedido(gestao_pb2.DadosConsulta(session_cookie=st.session_state.session_cookie, id_pedido=id_form))
        
        if response.livros:
            st.success("Pedido encontrado!")
            st.subheader("Detalhes do Pedido")
            
            # Exibir detalhes do pedido em um formato de tabela
            livros_data = {
                "Título": [livro.titulo for livro in response.livros],
            }
            df = pd.DataFrame(livros_data)
            st.table(df)
            
            st.subheader("Preço Total")
            st.metric(label="Preço Total (R$)", value=response.preco_total)
        else:
            st.error("Pedido não encontrado. Verifique o ID do pedido e tente novamente.")

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        auth_stub = auth_pb2_grpc.UserAuthStub(channel)
        catalog_stub = catalogo_pb2_grpc.ShowCatalogoStub(channel)
        gestao_stub = gestao_pb2_grpc.GestaoPedidosStub(channel)

        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login(auth_stub)
        else:
            catalog(catalog_stub, gestao_stub)

if __name__ == "__main__":
    run()
