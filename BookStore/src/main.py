import streamlit as st 
import pandas as pd
from server import df

# Inicializar a lista de livros selecionados
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# Configurar o título da aplicação
st.title('BookStore do DC')

# if st.button("Exibir catálogo", type="primary"):
st.write("Selecione os livros que deseja adicionar ao carrinho:")

# Adicionar checkboxes na tabela
edited_df = st.data_editor(df)

# Adicionar livros selecionados ao carrinho
if st.button("Confirmar Compra"):
    selected_books = [book for i, book in edited_df.iterrows() if book['Carrinho']]
    st.session_state.carrinho.extend(selected_books)
    st.success("Livros adicionados ao carrinho!")
    print(selected_books)


# st.button("Exibir pedidos e detalhes", type="primary")
# st.button("Exibir histórico", type="primary")
        