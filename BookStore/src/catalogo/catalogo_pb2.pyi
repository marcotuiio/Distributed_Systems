from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Session(_message.Message):
    __slots__ = ("session_cookie",)
    SESSION_COOKIE_FIELD_NUMBER: _ClassVar[int]
    session_cookie: str
    def __init__(self, session_cookie: _Optional[str] = ...) -> None: ...

class IdLivro(_message.Message):
    __slots__ = ("titulo",)
    TITULO_FIELD_NUMBER: _ClassVar[int]
    titulo: str
    def __init__(self, titulo: _Optional[str] = ...) -> None: ...

class ListCarrinho(_message.Message):
    __slots__ = ("livros_carrinho",)
    LIVROS_CARRINHO_FIELD_NUMBER: _ClassVar[int]
    livros_carrinho: _containers.RepeatedCompositeFieldContainer[IdLivro]
    def __init__(self, livros_carrinho: _Optional[_Iterable[_Union[IdLivro, _Mapping]]] = ...) -> None: ...

class Book(_message.Message):
    __slots__ = ("carrinho", "titulo", "autor", "publicacao", "em_estoque", "preco", "descricao")
    CARRINHO_FIELD_NUMBER: _ClassVar[int]
    TITULO_FIELD_NUMBER: _ClassVar[int]
    AUTOR_FIELD_NUMBER: _ClassVar[int]
    PUBLICACAO_FIELD_NUMBER: _ClassVar[int]
    EM_ESTOQUE_FIELD_NUMBER: _ClassVar[int]
    PRECO_FIELD_NUMBER: _ClassVar[int]
    DESCRICAO_FIELD_NUMBER: _ClassVar[int]
    carrinho: bool
    titulo: str
    autor: str
    publicacao: int
    em_estoque: int
    preco: int
    descricao: str
    def __init__(self, carrinho: bool = ..., titulo: _Optional[str] = ..., autor: _Optional[str] = ..., publicacao: _Optional[int] = ..., em_estoque: _Optional[int] = ..., preco: _Optional[int] = ..., descricao: _Optional[str] = ...) -> None: ...

class FullCatalogo(_message.Message):
    __slots__ = ("books",)
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class SuccessMessage(_message.Message):
    __slots__ = ("m", "id_pedido")
    M_FIELD_NUMBER: _ClassVar[int]
    ID_PEDIDO_FIELD_NUMBER: _ClassVar[int]
    m: str
    id_pedido: str
    def __init__(self, m: _Optional[str] = ..., id_pedido: _Optional[str] = ...) -> None: ...
