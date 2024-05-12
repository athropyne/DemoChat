import functools
from typing import Callable

from websockets import WebSocketServerProtocol

from core.exc import NonAuthorized
from core.user_cash import Cash
from services.accounts.models import GetOneUserModel


def protected(func: Callable):
    @functools.wraps(func)
    async def wrapper(_, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
        if not token or not isinstance(token, str) or Cash.online[socket.id].token != token:
            raise NonAuthorized()
        result = await func(_, socket, model, token)
        return result
    return wrapper
