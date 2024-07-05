from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class OpParam(_message.Message):
    __slots__ = ("val1", "val2")
    VAL1_FIELD_NUMBER: _ClassVar[int]
    VAL2_FIELD_NUMBER: _ClassVar[int]
    val1: int
    val2: int
    def __init__(self, val1: _Optional[int] = ..., val2: _Optional[int] = ...) -> None: ...

class OpResults(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: int
    def __init__(self, result: _Optional[int] = ...) -> None: ...
