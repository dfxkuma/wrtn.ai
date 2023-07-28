from typing import Any, Dict, Union


class WrtnException(Exception):
    pass


class HTTPException(WrtnException):
    def __init__(self, code: Any, message: Union[Any, Dict[str, Any]]) -> None:
        self.code = code
        self.message = message

        super().__init__(f"{self.code} {self.message}")


class ClientException(WrtnException):
    pass


class Forbidden(HTTPException):
    pass


class NotFound(HTTPException):
    pass


class ServerError(HTTPException):
    pass


class UserNotFound(ClientException):
    pass


class InvalidEmailVerifyCode(ClientException):
    pass
