import functools
from typing import Optional, Callable

from websockets import WebSocketServerProtocol

from core.cash import set_user_cash
from core.io import InternalError
from core.managers import UserCashModel, get_user_data_for_cash
from services.accounts.aliases import Ranks
from services.accounts.models import GetOneUserModel

permissions = {
    Ranks.GUEST: 0,
    Ranks.USER: 1,
    Ranks.SUPERVISOR: 2,
    Ranks.ADMINISTRATOR: 3
}


def permission(rank: Ranks, update_cash: bool):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(_, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
            if not token or not isinstance(token, str):  # если токен не передан  ( = None ) или не строка
                raise InternalError("вы не авторизованы")
            target_permission_level = permissions[rank]
            user = online[socket.id]
            if permissions[user.rank] < target_permission_level:  # если уровень допуска ниже чем нужно
                raise InternalError("недостаточно прав")
            result = await func(_, socket, model, token)
            if update_cash:
                ...
                # user_data: UserCashModel = await get_user_data_for_cash(user_id)
                # await set_user_cash(user_id, user_data)
            return result

        return wrapper

    return decorator
