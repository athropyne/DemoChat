from sqlalchemy import CursorResult, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets import WebSocketServerProtocol

from core import User
from core.base_event import BaseEvent
from core.database import engine
from core.io import InternalError, output
from core.schemas import rooms, locations, local_ranks
from core.user_cash import Cash
from services.accounts.aliases import AccountAliases
from services.accounts.events import Relocation
from services.accounts.models import RelocationModel
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import CreateRoomModel


class CreateRoom(BaseEvent):

    async def __create(self, db: AsyncConnection, data: dict) -> int:
        cursor: CursorResult = await db.execute(
            insert(rooms).values(data)
        )
        return cursor.lastrowid

    async def __update_location(self, db, room_id, user_id):
        cursor: CursorResult = await db.execute(
            update(locations)
            .values({RoomAliases.ID: room_id})
            .where(locations.c[AccountAliases.ID] == user_id)
        )

    async def __add_local_rank(self, db, room_id, user_id):
        await db.execute(
            insert(local_ranks).values({
                RoomAliases.ID: room_id,
                AccountAliases.ID: user_id,
                LocalRankAliases.rank: LocalRanks.OWNER
            })
        )

    # @permission(Ranks.USER, update_cash=False)
    async def __call__(self, socket: WebSocketServerProtocol, model: CreateRoomModel, token: str):
        user: User = Cash.online[socket.id]
        data: dict = model.model_dump(by_alias=True)
        async with engine.connect() as db:
            try:
                room_id = await self.__create(db, data)
            except IntegrityError as e:
                raise InternalError("такая комната уже есть")
            await self.__update_location(db, room_id, user.user_id)
            await self.__add_local_rank(db, room_id, user.user_id)
            await db.commit()
        await socket.send(output("комната создана"))
        await Relocation("")(socket, RelocationModel(**{RoomAliases.ID: room_id}), token)

