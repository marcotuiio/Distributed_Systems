from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DadosConsulta(_message.Message):
    __slots__ = ("session_cookie", "id_pedido")
    SESSION_COOKIE_FIELD_NUMBER: _ClassVar[int]
    ID_PEDIDO_FIELD_NUMBER: _ClassVar[int]
    session_cookie: str
    id_pedido: str
    def __init__(self, session_cookie: _Optional[str] = ..., id_pedido: _Optional[str] = ...) -> None: ...

class IdLivro(_message.Message):
    __slots__ = ("titulo",)
    TITULO_FIELD_NUMBER: _ClassVar[int]
    titulo: str
    def __init__(self, titulo: _Optional[str] = ...) -> None: ...

class StatusPedido(_message.Message):
    __slots__ = ("livros", "preco_total", "dono_pedido")
    LIVROS_FIELD_NUMBER: _ClassVar[int]
    PRECO_TOTAL_FIELD_NUMBER: _ClassVar[int]
    DONO_PEDIDO_FIELD_NUMBER: _ClassVar[int]
    livros: _containers.RepeatedCompositeFieldContainer[IdLivro]
    preco_total: int
    dono_pedido: str
    def __init__(self, livros: _Optional[_Iterable[_Union[IdLivro, _Mapping]]] = ..., preco_total: _Optional[int] = ..., dono_pedido: _Optional[str] = ...) -> None: ...

class DadosUser(_message.Message):
    __slots__ = ("session_cookie",)
    SESSION_COOKIE_FIELD_NUMBER: _ClassVar[int]
    session_cookie: str
    def __init__(self, session_cookie: _Optional[str] = ...) -> None: ...

class HistorioUser(_message.Message):
    __slots__ = ("livros",)
    LIVROS_FIELD_NUMBER: _ClassVar[int]
    livros: _containers.RepeatedCompositeFieldContainer[IdLivro]
    def __init__(self, livros: _Optional[_Iterable[_Union[IdLivro, _Mapping]]] = ...) -> None: ...
