from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class UserData(_message.Message):
    __slots__ = ("login_email", "login_senha")
    LOGIN_EMAIL_FIELD_NUMBER: _ClassVar[int]
    LOGIN_SENHA_FIELD_NUMBER: _ClassVar[int]
    login_email: str
    login_senha: str
    def __init__(self, login_email: _Optional[str] = ..., login_senha: _Optional[str] = ...) -> None: ...

class LoginResponse(_message.Message):
    __slots__ = ("response", "session_cookie", "message")
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    SESSION_COOKIE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    response: bool
    session_cookie: str
    message: str
    def __init__(self, response: bool = ..., session_cookie: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
