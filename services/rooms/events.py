from typing import Optional

from pydantic import BaseModel
from sqlalchemy import CursorResult, insert, update, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.exc import DuplicateError, InternalError, AccessDenied
from core.io import output
from core.out_events import Successfully, OnlineRoomList
from core.schemas import rooms, locations, local_ranks
from core.security import protected
from core.user_cash import online, User, Cash
from services.accounts.aliases import AccountAliases
from services.accounts.events import Relocation
from services.accounts.models import RelocationModel
from services.models import Paginator
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import CreateRoomModel, AddLocalPermissionModel, local_rank_level


class CreateRoom(BaseEvent):

    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: CreateRoomModel, token: Optional[str]):
        super().__init__(socket, model, token)

    async def __create(self, db: AsyncConnection, data: dict) -> int:
        cursor: CursorResult = await db.execute(
            insert(rooms).values(data)
        )
        return cursor.inserted_primary_key[0]

    async def __update_location(self, db: AsyncConnection, room_id: int, user_id: int):
        await db.execute(
            update(locations)
            .values({RoomAliases.ID: room_id})
            .where(locations.c[AccountAliases.ID] == user_id)
        )

    async def __add_local_rank(self, db: AsyncConnection, room_id: int, user_id: int):
        await db.execute(
            insert(local_ranks).values({
                RoomAliases.ID: room_id,
                AccountAliases.ID: user_id,
                LocalRankAliases.rank: LocalRanks.OWNER.name
            })
        )

    async def __call__(self):
        user: User = Cash.online[self.socket.id]
        data: dict = self.model.model_dump(by_alias=True)
        async with engine.connect() as db:
            try:
                room_id = await self.__create(db, data)
            except IntegrityError as e:
                raise DuplicateError("такая комната уже есть")
            await self.__update_location(db, room_id, user.ID)
            await self.__add_local_rank(db, room_id, user.ID)
            await db.commit()
        await self.socket.send(output("комната создана"))


class GetOnlineRoomList(BaseEvent):

    def __init__(self, socket: WebSocketServerProtocol, model: Paginator, token: Optional[str]):
        super().__init__(socket, model, token)

    async def __call__(self):
        location_id = Cash.online[self.socket.id].location_id
        sockets_in_room = Cash.location[location_id]
        users_in_room = [{
            AccountAliases.ID: Cash.online[s].ID,
            AccountAliases.nickname: Cash.online[s].nickname,
            LocalRankAliases.rank: Cash.online[s].local_rank
        } for s in sockets_in_room]
        await OnlineRoomList()(self.socket, model=users_in_room)


class UpdatePermission(BaseEvent):
    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: AddLocalPermissionModel, token: Optional[str]):
        super().__init__(socket, model, token)

    async def __get_local_rank_target_user(self, connection: AsyncConnection, user_id: int, room_id: int):
        cursor: CursorResult = await connection.execute(
            select(local_ranks.c[LocalRankAliases.rank])
            .where(local_ranks.c[AccountAliases.ID] == user_id)
            .where(local_ranks.c[RoomAliases.ID] == room_id)
        )
        return cursor.scalar()

    async def __clear_data_stmt(self, connection: AsyncConnection, target_user_id: int, location_id: int):
        await connection.execute(
            delete(local_ranks)
            .where(local_ranks.c[AccountAliases.ID] == target_user_id)
            .where(local_ranks.c[RoomAliases.ID] == location_id)
        )

    async def __update_data_stmt(self, connection: AsyncConnection,
                                 target_user_id: int,
                                 location_id: int,
                                 rank: LocalRanks):
        await connection.execute(
            insert(local_ranks).values(
                {
                    AccountAliases.ID: target_user_id,
                    RoomAliases.ID: location_id,
                    LocalRankAliases.rank: rank
                }
            )
        )

    async def __call__(self):
        requester_user: User = Cash.online[self.socket.id]
        async with engine.connect() as connection:
            target_user_local_rank = await self.__get_local_rank_target_user(
                connection=connection,
                user_id=self.model.target_user_id,
                room_id=Cash.online[self.socket.id].location_id
            )
        if target_user_local_rank is None:
            target_user_local_rank = LocalRanks.USER

        if local_rank_level[requester_user.local_rank] > local_rank_level[LocalRanks.USER]:
            if local_rank_level[requester_user.local_rank] > local_rank_level[self.model.rank]:
                if local_rank_level[requester_user.local_rank] > local_rank_level[target_user_local_rank]:
                    async with engine.connect() as connection:
                        await self.__clear_data_stmt(connection, self.model.target_user_id, requester_user.location_id)
                        if self.model.rank is not LocalRanks.USER:
                            await self.__update_data_stmt(connection,
                                                          self.model.target_user_id,
                                                          requester_user.location_id,
                                                          self.model.rank)

                        await connection.commit()
                        if self.model.target_user_id in Cash.ids:
                            socket_id = Cash.ids[self.model.target_user_id]
                            Cash.online[socket_id].local_rank = self.model.rank
                        await Successfully()(self.socket, model="ранг изменен")
                else:
                    raise AccessDenied("ваш ранг должен быть выше чем у целевого пользователя")
            else:
                raise AccessDenied("ваш ранг должен быть выше устанавливаемого")
        else:
            raise AccessDenied("ваш ранг должен быть выше чем USER")
