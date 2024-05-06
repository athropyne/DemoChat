from sqlalchemy import CursorResult, insert, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.io import InternalError, output
from core.schemas import rooms, locations, local_ranks
from core.security import protected
from core.user_cash import online, UserLink
from services.accounts.aliases import AccountAliases
from services.accounts.events import Relocation
from services.accounts.models import RelocationModel
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import CreateRoomModel, AddLocalPermissionModel, local_permission_level


class CreateRoom(BaseEvent):

    async def __create(self, db: AsyncConnection, data: dict) -> int:
        cursor: CursorResult = await db.execute(
            insert(rooms).values(data)
        )
        return cursor.lastrowid

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
                LocalRankAliases.rank: LocalRanks.OWNER
            })
        )

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: CreateRoomModel, token: str):
        user: UserLink = online[socket.id]
        data: dict = model.model_dump(by_alias=True)
        async with engine.connect() as db:
            try:
                room_id = await self.__create(db, data)
            except IntegrityError as e:
                raise InternalError("такая комната уже есть")
            await self.__update_location(db, room_id, user.ID)
            await self.__add_local_rank(db, room_id, user.ID)
            await db.commit()
        await socket.send(output("комната создана"))
        await Relocation("")(socket, RelocationModel(**{RoomAliases.ID: room_id}), token)


class UpdatePermission(BaseEvent):
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

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: AddLocalPermissionModel, token: str):
        requester_user: User = Cash.online[socket.id]
        target_user: User = Cash.ids[model.target_user_id]
        lpl: dict = local_permission_level
        rur: LocalRanks = requester_user.local_rank
        tur: LocalRanks = target_user.local_rank
        if requester_user.location_id == target_user.location_id:
            if lpl[rur] > lpl[tur]:
                if lpl[rur] > lpl[model.rank]:
                    async with engine.connect() as connection:
                        await self.__clear_data_stmt(connection, model.target_user_id, requester_user.location_id)
                        if model.rank is not None:
                            await self.__update_data_stmt(connection,
                                                          model.target_user_id,
                                                          requester_user.location_id,
                                                          model.rank)

                        await connection.commit()
                        Cash.ids[target_user.user_id].local_rank = model.rank
                else:
                    raise InternalError("операция не доступна", "ваш ранг должен быть выше устанавливаемого")
            else:
                raise InternalError("операция не доступна", "ваш ранг должен быть выше чем у целевого пользователя")
        else:
            raise InternalError("операция недоступна", "пользователь должен быть онлайн и в той же комнате")
