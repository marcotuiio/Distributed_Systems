# Trabalho de Sistemas Distribuidos              07/2024
## Marco Tulio Alves de Barros              202100560105

### Objetivos

Desenvolver um sistema de loja de livro usando RPC, com cliente e servidor
Será possível selecionar livros e comprá-los, ver o pedido, consultar pedidos, consultar histórico
No servidor estarão armazenados os livros e suas informações, além de um sistema de autenticação

Trabalhar com as interfaces do modelo RPC, snedo que deverá ser um trabalho devidamente modularizado

### Rodando

#### OBS !!!
Como os arquivos gerados estão em pastas separadas talvez seja preciso arrumar os imports para 
que funcione devidamente :

Em auth_pb2_grpc.py: import auth_pb2 as auth__pb2 para import auth.auth_pb2 as auth__pb2
Em catalogo_pb2_grpc: import catalogo_pb2 as catalogo__pb2 para import catalogo.catalogo_pb2 as catalogo__pb2
Em gestao_pb2_grpc: import gestao_pb2 as gestao__pb2 para import gestao.gestao_pb2 as gestao__pb2

* 1º Rodar o comando: pip install -r requirements.txt
* 2º Rodar o comando: sudo apt install protobuf-compiler

* 3º No diretorio BookStore/ rodar para gerar os arqs novamente (atenção com a observação):

- python3 -m grpc_tools.protoc -I protos --python_out=src/catalogo/ --pyi_out=src/catalogo/ --grpc_python_out=src/catalogo/ protos/catalogo.proto

- python3 -m grpc_tools.protoc -I protos --python_out=src/auth/ --pyi_out=src/auth/ --grpc_python_out=src/auth/ protos/auth.proto

- python3 -m grpc_tools.protoc -I protos --python_out=src/gestao/ --pyi_out=src/gestao/ --grpc_python_out=src/gestao/ protos/gestao.proto

* 4º No diretorio BookStore/src rodar (em dois terminais separados)

- python3 server.py

- streamlit run client.py