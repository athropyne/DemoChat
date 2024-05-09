import asyncio
from typing import Optional
from uuid import UUID

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from redis.asyncio import Redis
from sqlalchemy import CursorResult, insert, select, update, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.base import ReadOnlyColumnCollection
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.exc import InternalError, DuplicateError, InvalidDataError, NotFoundError, UpdateError
from core.io import output
from core.managers import Token, PasswordManager
from core.out_events import Successfully, OneUserInfo, OnlineUserListInfo, SystemMessage
from core.schemas import accounts, locations, local_ranks, rooms
from core.security import protected
from core.user_cash import UserLink, online, Storage, UserCash, set_user_cash
from services.accounts.aliases import AccountAliases, AccountStatuses
from services.accounts.models import CreateModel, AuthModel, GetOneUserOut, GetOneUserModel, GetOnlineUserListModel, \
    ChangeNickModel, RelocationModel, ChangePasswordModel, AuthModelOut
from services.messages.aliases import PublicAliases
from services.messages.events import SendPublic
from services.messages.models import NewPublicModel, PublicMessageOut, Author
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import LocationShortInfoModel


class Create(BaseEvent):

    async def __create_user(self, db: AsyncConnection, data: dict):
        try:
            cursor: CursorResult = await db.execute(
                insert(accounts).values(**data)
            )
            return cursor.inserted_primary_key[0]
        except IntegrityError as e:
            if isinstance(e.orig.__cause__, UniqueViolationError):
                raise DuplicateError("такой ник уже существует")
            raise InternalError("внутренняя ошибка")

    async def __add_location(self, db: AsyncConnection, user_id: int):
        await db.execute(
            insert(locations).values({
                AccountAliases.ID: user_id,
                RoomAliases.ID: None})
        )

    async def __call__(self, socket: WebSocketServerProtocol, model: CreateModel, token: str):
        container = model.model_dump(by_alias=True)
        container[AccountAliases.password] = PasswordManager.get_hash(model.password)
        async with engine.connect() as db:
            user_id = await self.__create_user(db, container)
            await self.__add_location(db, user_id)
            await db.commit()
        token = Token.generate()
        online[socket.id].ID = user_id
        online[socket.id].token = token
        cash = UserCash(ID=user_id, token=token, nickname=model.nickname).model_dump(exclude_none=True)
        async with Storage() as storage:
            await set_user_cash(storage, cash)
        # await socket.send(output("успешная регистрация", {"токен": token}))

        await Successfully()({socket}, AuthModelOut(token=token), self.name)


class Auth(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    async def __get_user(self, nickname: str) -> Optional[dict]:
        async with engine.connect() as db:
            cursor = await db.execute(
                select(
                    accounts.c[AccountAliases.ID],
                    accounts.c[AccountAliases.nickname],
                    accounts.c[AccountAliases.password],
                    locations.c[RoomAliases.ID],
                )
                .join(locations, accounts.c[AccountAliases.ID], isouter=True)
                .where(
                    accounts.c[AccountAliases.nickname] == nickname
                )
            )
            result = cursor.mappings().fetchone()
            result = None if not result else dict(result)
            return result

    async def __get_local_rank(self, db: AsyncConnection, user_id: int, room_id: int):
        local_rank_cursor: CursorResult = await db.execute(
            select(local_ranks.c[LocalRankAliases.rank])
            .where(local_ranks.c[AccountAliases.ID] == user_id)
            .where(local_ranks.c[RoomAliases.ID] == room_id)
        )
        return local_rank_cursor.scalar()

    async def __call__(self, socket: WebSocketServerProtocol, model: AuthModel, token: str) -> None:
        user: Optional[dict] = await self.__get_user(model.nickname)
        if user is not None:
            if not PasswordManager.verify_hash(model.password, user[AccountAliases.password]):
                raise InvalidDataError("неверный пароль")
            else:
                if user[RoomAliases.ID] is not None:
                    async with engine.connect() as db:
                        user[LocalRankAliases.rank] = await self.__get_local_rank(db, user[AccountAliases.ID],
                                                                                  user[RoomAliases.ID])
                token = Token.generate()
                online[socket.id].ID = user[AccountAliases.ID]
                online[socket.id].token = token
                cash: dict = UserCash(
                    ID=user[AccountAliases.ID],
                    token=token,
                    nickname=model.nickname,
                    location_id=user[RoomAliases.ID],
                    location_rank=user.get(LocalRankAliases.rank)
                ).model_dump(exclude_none=True)
                async with Storage() as storage:
                    await set_user_cash(storage, cash)
                await Successfully()({socket}, AuthModelOut(token=token), self.name)
        else:
            raise NotFoundError("пользователя не существует")


class GetOneUser(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    async def __get_info(self, db: AsyncConnection, user_id: int) -> Optional[dict]:
        cursor: CursorResult = await db.execute(
            select(
                accounts.c[AccountAliases.ID],
                accounts.c[AccountAliases.nickname],
                accounts.c[AccountAliases.created_at],
                rooms.c[RoomAliases.ID],
                rooms.c[RoomAliases.title]
            )
            .join(locations, locations.c[AccountAliases.ID] == accounts.c[AccountAliases.ID])
            .join(rooms, rooms.c[RoomAliases.ID] == locations.c[RoomAliases.ID], isouter=True)
            .where(accounts.c[AccountAliases.ID] == user_id)
        )
        return cursor.mappings().fetchone()

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
        async with engine.connect() as storage:
            result: Optional[dict] = await self.__get_info(storage, model.ID)
        if not result:
            raise NotFoundError("пользователь не найден")
        async with Storage() as storage:
            is_online = await storage.exists(f"user:{result[AccountAliases.ID]}")
        mess_out = GetOneUserOut(
            **{
                AccountAliases.ID: result[AccountAliases.ID],
                AccountAliases.nickname: result[AccountAliases.nickname],
                AccountAliases.created_at: result[AccountAliases.created_at],
                AccountAliases.status: AccountStatuses.ONLINE if is_online else AccountStatuses.OFFLINE,
                AccountAliases.location: LocationShortInfoModel(
                    **{
                        RoomAliases.ID: result[RoomAliases.ID],
                        RoomAliases.title: result[RoomAliases.title]
                    }
                ).model_dump(by_alias=True),
            }
        )
        await OneUserInfo()({socket}, GetOneUserOut(**mess_out.model_dump(by_alias=True)), self.name)
        # await socket.send(output("информация о пользователе",
        #                          GetOneUserOut(**mess_out.model_dump(by_alias=True)).model_dump(by_alias=True)))


class GetOnlineUserList(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    async def __get_one_from_cash(self, connection: Redis, top_level_key: str):
        return await connection.hmget(top_level_key, ["ID", "nickname", "location_id"])

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: GetOnlineUserListModel, token: str):
        async with Storage() as connection:
            top_level_keys: list = await connection.keys("user:*")
            result = await asyncio.gather(*[self.__get_one_from_cash(connection, k) for k in top_level_keys])

        result = [{AccountAliases.ID: int(i[0]),
                   AccountAliases.nickname: i[1],
                   AccountAliases.location: None if not i[2] else int(i[2])} for i in result]
        await OnlineUserListInfo()({socket}, result, self.name)


class ChangeNick(BaseEvent):
    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: ChangeNickModel, token: str):
        user: UserLink = online[socket.id]

        async with engine.connect() as connection:
            try:
                cursor: CursorResult = await connection.execute(
                    update(accounts)
                    .values({AccountAliases.nickname: model.nickname})
                    .where(accounts.c[AccountAliases.ID] == user.ID)
                )
                if cursor.rowcount != 1:
                    await connection.rollback()
                    raise UpdateError("ник не изменен")
            except IntegrityError as e:
                raise DuplicateError("такой ник уже существует")
        cash = UserCash(ID=user.ID, nickname=model.nickname).model_dump(exclude_none=True)
        async with Storage() as storage:
            await set_user_cash(storage, cash)
        await Successfully()({socket}, "ник изменен", None)


class ChangePassword(BaseEvent):

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: ChangePasswordModel, token: str):
        user: UserLink = online[socket.id]
        new_password = PasswordManager.get_hash(model.password)
        async with engine.connect() as connection:
            cursor: CursorResult = await connection.execute(
                update(accounts)
                .values({AccountAliases.password: new_password})
                .where(accounts.c[AccountAliases.ID] == user.ID)
            )
            if cursor.rowcount != 1:
                await connection.rollback()
                raise UpdateError("пароль не изменен")
        await Successfully()({socket}, "ник изменен", None)


class Relocation(BaseEvent):

    async def __relocate(self, db: AsyncConnection, user_id: int, room_id: int):
        try:
            await db.execute(
                update(locations).values({RoomAliases.ID: room_id}).where(
                    locations.c[AccountAliases.ID] == user_id)
            )
            await db.commit()
        except IntegrityError as e:
            if isinstance(e.orig.__cause__, ForeignKeyViolationError):
                raise InvalidDataError(f"комнаты с ID {room_id} не существует")
            raise InternalError("внутренняя ошибка")

    async def __get_target_room_rank_and_title(self, db: AsyncConnection, user_id: int, room_id: int):
        lr = select(
            local_ranks.c[LocalRankAliases.rank]
        ).where(
            local_ranks.c[AccountAliases.ID] == user_id
        ).where(
            local_ranks.c[RoomAliases.ID] == room_id
        ).scalar_subquery().label(LocalRankAliases.rank)
        cursor: CursorResult = await db.execute(
            select(
                rooms.c[RoomAliases.title],
                lr
            )
            .where(rooms.c[RoomAliases.ID] == room_id)
        )
        return cursor.mappings().fetchone()

    async def __get_sockets_in_room(self, connection: Redis, top_level_key: str):
        return await connection.hgetall(top_level_key)

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: RelocationModel, token: str):
        user: UserLink = online[socket.id]
        send_public = SendPublic("")
        async with engine.connect() as db:
            await self.__relocate(db, user.ID, model.room_id)
            result: Optional[RowMapping] = await self.__get_target_room_rank_and_title(db, user.ID,
                                                                                       model.room_id)
        new_cash = UserCash(ID=user.ID, location_id=model.room_id, local_rank=result[LocalRankAliases.rank])
        async with Storage() as storage:
            location_id, local_rank, nickname = await storage.hmget(
                f"user:{user.ID}",
                "location_id",
                "local_rank",
                "nickname"
            )

            pipline = storage.pipeline()
            if location_id:
                pipline.hdel(
                    f"location:{location_id}",
                    user.ID
                )
            pipline.hset(
                f"location:{model.room_id}",
                user.ID,
                socket.id.hex
            )
            pipline.hset(
                name=f"user:{new_cash.ID}",
                mapping=new_cash.model_dump(exclude_none=True)
            )
            await pipline.execute()

            current_room_sockets, target_room_sockets = await asyncio.gather(
                *[self.__get_sockets_in_room(storage, i) for i in
                  (f"location:{location_id}", f"location:{model.room_id}")]
            )
            print(f"{current_room_sockets=}")
            print(f"{target_room_sockets=}")
        await SystemMessage()(
            {online[UUID(s)].socket for s in current_room_sockets.values()},
            PublicMessageOut(
                text=f"[{nickname} перешел в комнату {result[RoomAliases.title]}]",
                author=Author(
                    user_id=user.ID,
                    nickname=nickname,
                    local_rank=local_rank,
                )
            )
        )
        await SystemMessage()(
            {online[UUID(s)].socket for s in target_room_sockets.values()},
            PublicMessageOut(
                text=f"[{nickname} вошел в комнату]",
                author=Author(
                    user_id=user.ID,
                    nickname=nickname,
                    local_rank=result[LocalRankAliases.rank],
                )
            )
        )

        # await SystemMessage()(
        #     current_room_sockets,
        #     NewPublicModel(**{PublicAliases.text: f"[{nickname} вошел в комнату]"}))
