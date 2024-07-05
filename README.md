# Trabalho de Sistemas Distribuidos              07/2024
## Marco Tulio Alves de Barros              202100560105

### Objetivos

Desenvolver um sistema de loja de livro usando RPC, com cliente e servidor
Será possível selecionar livros e comprá-los, ver o pedido, consultar pedidos, consultar histórico
No servidor estarão armazenados os livros e suas informações, além de um sistema de autenticação

Trabalhar com as interfaces do modelo RPC, snedo que deverá ser um trabalho devidamente modularizado

### Rodando

* 1º Rodar o comando: pip install -r requirements.txt
* 2º Rodar o comando: sudo apt install protobuf-compiler

python3 -m grpc_tools.protoc -I protos --python_out=src/catalogo/ --pyi_out=src/catalogo/ --grpc_python_out=src/catalogo/ protos/catalogo.proto