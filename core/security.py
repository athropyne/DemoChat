import functools
from typing import Callable

from websockets import WebSocketServerProtocol

from core.io import InternalError
from core.user_cash import online
from services.accounts.models import GetOneUserModel


def protected(func: Callable):
    @functools.wraps(func)
    async def wrapper(_, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
        if not token or not isinstance(token, str) or online[socket.id].token != token:
            raise InternalError("вы не авторизованы")
        result = await func(_, socket, model, token)
        return result
    return wrapper
