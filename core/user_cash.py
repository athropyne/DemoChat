from dataclasses import dataclass
from typing import Optional, Dict, Set
from uuid import UUID
import weakref
from redis.asyncio import Redis
import redis
from pydantic import BaseModel
from websockets import WebSocketServerProtocol

from services.rooms.aliases import LocalRanks

USER_ID = int
ROOM_ID = int


@dataclass
class UserLink:
    socket: WebSocketServerProtocol
    ID: Optional[USER_ID] = None
    token: Optional[str] = None


class UserCash(BaseModel):
    ID: USER_ID
    token: str
    nickname: str
    local_rank: Optional[LocalRanks] = None
    location_id: Optional[ROOM_ID] = None


class User:
    __slots__ = [
        "socket",
        "token",
        "__user_id",
        "nickname",
        "local_rank",
        "__location_id",
    ]

    def __init__(
            self,
            socket: WebSocketServerProtocol,

    ):
        self.__location_id = None
        self.local_rank = None
        self.nickname = None
        self.__user_id = None
        self.token = None
        self.socket = socket

    @property
    def location_id(self):
        return self.__location_id

    @location_id.setter
    def location_id(self, value):
        print(f"{value=}")
        if value not in Cash.channels and value is not None:
            Cash.channels[value] = set()
            if self.__location_id is not None:
                Cash.channels[self.__location_id].remove(self)
            Cash.channels[value].add(self)
        self.__location_id = value

    @property
    def user_id(self):
        return self.__user_id

    @user_id.setter
    def user_id(self, value):
        Cash.ids[value] = self
        self.__user_id = value


online: Dict[UUID, UserLink] = {}


class Storage:
    async def __aenter__(self):
        self.connection: Redis = Redis(decode_responses=True)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection.close()


class Cash:
    online: Dict[UUID, UserLink] = {}
    channels: Dict[Optional[int], Set[User]] = {}
    ids: Dict[int, User] = {}
