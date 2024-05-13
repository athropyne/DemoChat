from dataclasses import dataclass
from typing import Optional, Dict, Set
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis
from websockets import WebSocketServerProtocol

from services.rooms.aliases import LocalRanks

USER_ID = int
ROOM_ID = int
SOCKET_ID = UUID


# @dataclass
# class UserLink:
#     socket: WebSocketServerProtocol
#     ID: Optional[USER_ID] = None
#     token: Optional[str] = None


class User:
    __slots__ = [
        "socket",
        "token",
        "__ID",
        "nickname",
        "local_rank",
        "__location_id",
    ]

    def __init__(
            self,
            socket: WebSocketServerProtocol
    ):
        self.__location_id: Optional[int] = None
        self.local_rank: Optional[LocalRanks] = None
        self.nickname: Optional[str] = None
        self.__ID: Optional[int] = None
        self.token: Optional[str] = None
        self.socket: WebSocketServerProtocol = socket

    @property
    def ID(self):
        return self.__ID

    @ID.setter
    def ID(self, value):
        self.__ID = value
        Cash.ids[value] = self.socket.id

    @property
    def location_id(self):
        return self.__location_id

    @location_id.setter
    def location_id(self, value):
        if self.location_id is not None:
            Cash.location[self.location_id].remove(self.socket.id)
            if len(Cash.location[self.location_id]) == 0:
                del Cash.location[self.location_id]
        if value not in Cash.location:
            Cash.location[value] = set()
        Cash.location[value].add(self.socket.id)
        self.__location_id = value


class Cash:
    online: Dict[SOCKET_ID, User] = {}
    ids: Dict[USER_ID, SOCKET_ID] = {}
    location: Dict[ROOM_ID, Set[SOCKET_ID]] = {}



online: Dict[SOCKET_ID, User] = {}
location: Dict[ROOM_ID, Set[SOCKET_ID]] = {}
# class Storage:
#
#     async def __aenter__(self):
#         self.connection: Redis = Redis(decode_responses=True)
#         return self.connection
#
#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         # if exc_type:
#         #     raise InternalError("внутренняя ошибка", "ошибка обновления кэша")
#         await self.connection.close()
#
#
# async def set_user_cash(storage: Redis, data: dict):
#     await storage.hset(
#         name=f"user:{data['ID']}",
#         mapping=data
#     )
