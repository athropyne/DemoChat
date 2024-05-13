import asyncio
from typing import Optional
from uuid import UUID

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import CursorResult, insert, select, update, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.config import TOKEN_EXPIRE
from core.database import engine
from core.exc import InternalError, DuplicateError, InvalidDataError, NotFoundError, UpdateError
from core.managers import Token, PasswordManager
from core.out_events import Successfully, OneUserInfo, OnlineUserListInfo, SystemMessage, NewToken
from core.schemas import accounts, locations, local_ranks, rooms
from core.security import protected
from core.user_cash import Cash, User
from services.accounts.aliases import AccountAliases, AccountStatuses
from services.accounts.models import CreateModel, AuthModel, GetOneUserOut, GetOneUserModel, GetOnlineUserListModel, \
    ChangeNickModel, RelocationModel, ChangePasswordModel, AuthModelOut
from services.messages.events import SendPublic
from services.messages.models import PublicMessageOut, Author
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import LocationShortInfoModel


class Create(BaseEvent):
    def __init__(self, socket: WebSocketServerProtocol, model: AuthModel, token=None):
        super().__init__(socket, model, token)

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
                RoomAliases.ID: 1})
        )

    async def __call__(self):
        container = self.model.model_dump(by_alias=True)
        container[AccountAliases.password] = PasswordManager.get_hash(self.model.password)
        async with engine.connect() as db:
            user_id = await self.__create_user(db, container)
            await self.__add_location(db, user_id)
            await db.commit()
        token = Token.generate()
        Cash.online[self.socket.id].ID = user_id
        Cash.online[self.socket.id].nickname = self.model.nickname
        Cash.online[self.socket.id].token = token
        Cash.online[self.socket.id].location_id = 1
        Cash.online[self.socket.id].local_rank = LocalRanks.USER
        Cash.online[self.socket.id].token = token
        await Successfully()(self.socket, model="успешная регистрация")
        await NewToken()(self.socket, model=AuthModelOut(token=token))


class Auth(BaseEvent):
    def __init__(self, socket: WebSocketServerProtocol, model: AuthModel, token=None):
        super().__init__(socket, model, token)

    async def __get_user(self, nickname: str) -> Optional[dict]:
        async with engine.connect() as db:
            cursor = await db.execute(
                select(
                    accounts.c[AccountAliases.ID],
                    accounts.c[AccountAliases.nickname],
                    accounts.c[AccountAliases.password],
                    locations.c[RoomAliases.ID],
                )
                .join(locations, accounts.c[AccountAliases.ID] == locations.c[AccountAliases.ID], isouter=True)
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

    async def __call__(self) -> None:
        user: Optional[dict] = await self.__get_user(self.model.nickname)
        if user is not None:
            if not PasswordManager.verify_hash(self.model.password, user[AccountAliases.password]):
                raise InvalidDataError("неверный пароль")
            else:
                if user[RoomAliases.ID] is not None:
                    async with engine.connect() as db:
                        user[LocalRankAliases.rank] = await self.__get_local_rank(db, user[AccountAliases.ID],
                                                                                  user[RoomAliases.ID])

                token = Token.generate()

                Cash.online[self.socket.id].ID = user[AccountAliases.ID]
                Cash.online[self.socket.id].nickname = self.model.nickname
                Cash.online[self.socket.id].token = token
                Cash.online[self.socket.id].location_id = user[RoomAliases.ID]
                Cash.online[self.socket.id].local_rank = LocalRanks.USER if user[LocalRankAliases.rank] is None else \
                    user[
                        LocalRankAliases.rank]
                Cash.online[self.socket.id].token = token
                print(Cash.online[self.socket.id].location_id)
                print(Cash.online[self.socket.id].local_rank)
                print(Cash.location)

                await Successfully()(self.socket, model="успешная авторизация")
                await NewToken()(self.socket, model=AuthModelOut(token=token))
        else:
            raise NotFoundError("пользователя не существует")


class GetOneUser(BaseEvent):
    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
        super().__init__(socket, model, token)

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

    async def __call__(self):
        async with engine.connect() as storage:
            result: Optional[dict] = await self.__get_info(storage, self.model.ID)
        if not result:
            raise NotFoundError("пользователь не найден")
        status = AccountStatuses.ONLINE if result[AccountAliases.ID] in Cash.ids else AccountStatuses.OFFLINE
        mess_out = GetOneUserOut(
            **{
                AccountAliases.ID: result[AccountAliases.ID],
                AccountAliases.nickname: result[AccountAliases.nickname],
                AccountAliases.created_at: result[AccountAliases.created_at],
                AccountAliases.status: status,
                AccountAliases.location: LocationShortInfoModel(
                    **{
                        RoomAliases.ID: result[RoomAliases.ID],
                        RoomAliases.title: result[RoomAliases.title]
                    }
                ).model_dump(by_alias=True),
            }
        )
        await OneUserInfo()(self.socket, model=GetOneUserOut(**mess_out.model_dump(by_alias=True)))


class GetOnlineUserList(BaseEvent):
    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: GetOnlineUserListModel, token: Optional[str]):
        super().__init__(socket, model, token)

    async def __call__(self):
        result = [{
            AccountAliases.ID: u.ID,
            AccountAliases.nickname: u.nickname,
            AccountAliases.location: u.location_id
        } for u in Cash.online.values()]
        await OnlineUserListInfo()(self.socket, model=result)


class ChangeNick(BaseEvent):
    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: ChangeNickModel, token: Optional[str]):
        super().__init__(socket,model, token)

    async def __call__(self):
        user: User = Cash.online[self.socket.id]

        async with engine.connect() as connection:
            try:
                cursor: CursorResult = await connection.execute(
                    update(accounts)
                    .values({AccountAliases.nickname: self.model.nickname})
                    .where(accounts.c[AccountAliases.ID] == user.ID)
                )
                if cursor.rowcount != 1:
                    await connection.rollback()
                    raise UpdateError("ник не изменен")
            except IntegrityError as e:
                if isinstance(e.orig.__cause__, UniqueViolationError):
                    raise DuplicateError("такой ник уже существует")
                raise InternalError("внутренняя ошибка")
            await connection.commit()
        user.nickname = self.model.nickname

        await Successfully()(self.socket, model="ник изменен")


class ChangePassword(BaseEvent):

    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: ChangePasswordModel, token: Optional[str]):
        super().__init__(socket,model, token)

    async def __call__(self):
        user: User = Cash.online[self.socket.id]
        new_password = PasswordManager.get_hash(self.model.password)
        async with engine.connect() as connection:
            cursor: CursorResult = await connection.execute(
                update(accounts)
                .values({AccountAliases.password: new_password})
                .where(accounts.c[AccountAliases.ID] == user.ID)
            )
            if cursor.rowcount != 1:
                await connection.rollback()
                raise UpdateError("пароль не изменен")
        await Successfully()(self.socket, model="ник изменен")


class Relocation(BaseEvent):

    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: RelocationModel, token: Optional[str]):
        super().__init__(socket, model, token)

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

    async def __call__(self):
        user: User = Cash.online[self.socket.id]
        async with engine.connect() as db:
            await self.__relocate(db, user.ID, self.model.room_id)
            result: Optional[RowMapping] = await self.__get_target_room_rank_and_title(db, user.ID,
                                                                                       self.model.room_id)

        await SystemMessage()(
            *{Cash.online[sid].socket for sid in Cash.location[user.location_id] if self.socket != Cash.online[sid].socket},
            model=PublicMessageOut(
                text=f"[{user.nickname} перешел в комнату {result[RoomAliases.title]}]",
                creator=Author(
                    user_id=user.ID,
                    nickname=user.nickname,
                    local_rank=user.local_rank,
                )
            )
        )

        user.location_id = self.model.room_id
        user.local_rank = result[LocalRankAliases.rank] if result[
                                                               LocalRankAliases.rank] is not None else LocalRanks.USER

        await SystemMessage()(
            *{Cash.online[sid].socket for sid in Cash.location[self.model.room_id]},
            model=PublicMessageOut(
                text=f"[{user.nickname} вошел в комнату]",
                creator=Author(
                    user_id=user.ID,
                    nickname=user.nickname,
                    local_rank=user.local_rank,
                )
            )
        )


