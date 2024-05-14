import functools
from typing import Callable

from pydantic import BaseModel
from websockets import WebSocketServerProtocol

from events.exc import NonAuthorized
from core.user_cash import Cash


def protected(func: Callable):
    @functools.wraps(func)
    def wrapper(_, socket: WebSocketServerProtocol, model: BaseModel, token: str):
        if not token or not isinstance(token, str) or Cash.online[socket.id].token != token:
            raise NonAuthorized()
        result = func(_, socket, model, token)
        return result
    return wrapper
