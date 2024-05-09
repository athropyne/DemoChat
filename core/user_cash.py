from dataclasses import dataclass
from typing import Optional, Dict
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis
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
    ID: Optional[USER_ID] = None
    token: Optional[str] = None
    nickname: Optional[str] = None
    local_rank: Optional[LocalRanks] = None
    location_id: Optional[ROOM_ID] = None


online: Dict[UUID, UserLink] = {}


class Storage:

    async def __aenter__(self):
        self.connection: Redis = Redis(decode_responses=True)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # if exc_type:
        #     raise InternalError("внутренняя ошибка", "ошибка обновления кэша")
        await self.connection.close()


async def set_user_cash(storage: Redis, data: dict):
    await storage.hset(
        name=f"user:{data['ID']}",
        mapping=data
    )
