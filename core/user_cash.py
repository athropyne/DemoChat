from typing import Optional, Dict, Set
from uuid import UUID
import weakref

from websockets import WebSocketServerProtocol


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



class Cash:
    online: Dict[UUID, User] = {}
    channels: Dict[Optional[int], Set[User]] = {}
    ids: Dict[int, User] = {}
