import asyncio
from typing import Optional, Type

from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import CursorResult, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets import WebSocketServerProtocol

from core import User
from core.base_event import BaseEvent
from core.database import engine
from core.io import InternalError, output
from core.managers import Token, PasswordManager
from core.schemas import accounts, locations, local_ranks, rooms
from core.security import protected
from core.user_cash import Cash, UserLink, online, Storage, UserCash
from services.accounts.aliases import AccountAliases, AccountStatuses
from services.accounts.models import CreateModel, AuthModel, GetOneUserOut, GetOneUserModel, GetOnlineUserListModel, \
    ChangeNickModel, RelocationModel, ChangePasswordModel
from services.messages.aliases import PublicAliases
from services.messages.events import SendPublic
from services.messages.models import NewPublicModel
from services.rooms.aliases import RoomAliases, LocalRankAliases, LocalRanks
from services.rooms.models import LocationShortInfoModel


class Create(BaseEvent):

    async def __call__(self, socket: WebSocketServerProtocol, model: CreateModel, token: str):
        container = model.model_dump(by_alias=True)
        container[AccountAliases.password] = PasswordManager.get_hash(model.password)
        async with engine.connect() as db:
            try:
                cursor: CursorResult = await db.execute(
                    insert(accounts).values(**container)
                )
                user_id = cursor.lastrowid
            except IntegrityError as e:
                raise InternalError("такой ник уже существует")
            await db.execute(
                insert(locations).values({
                    AccountAliases.ID: user_id,
                    RoomAliases.ID: None})
            )
            await db.commit()
        token = Token.generate()
        online[socket.id].ID = user_id
        online[socket.id].token = token
        async with Storage() as connection:
            await connection.hset(
                name=f"user:{user_id}",
                mapping=UserCash(
                    ID=user_id,
                    token=token,
                    nickname=model.nickname
                ).model_dump(exclude_none=True)
            )

        await socket.send(output("успешная регистрация", {"токен": token}))


class Auth(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    @staticmethod
    async def __get_user(model: AuthModel) -> Optional[dict]:
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
                    accounts.c[AccountAliases.nickname] == model.nickname
                )
            )
            result = cursor.mappings().fetchone()
            result = None if not result else dict(result)
            return result

    async def __call__(self, socket: WebSocketServerProtocol, model: AuthModel, token: str) -> None:
        user: Optional[dict] = await Auth.__get_user(model)
        if user is not None:
            if not PasswordManager.verify_hash(model.password, user[AccountAliases.password]):
                raise InternalError("неверный пароль")
            else:
                if user[RoomAliases.ID] is not None:
                    async with engine.connect() as connection:
                        local_rank_cursor: CursorResult = await connection.execute(
                            select(local_ranks.c[LocalRankAliases.rank])
                            .where(local_ranks.c[AccountAliases.ID] == user[AccountAliases.ID])
                            .where(local_ranks.c[RoomAliases.ID] == user[RoomAliases.ID])
                        )
                        user[LocalRankAliases.rank] = local_rank_cursor.scalar()
                token = Token.generate()
                online[socket.id].ID = user[AccountAliases.ID]
                online[socket.id].token = token
                async with Storage() as connection:
                    await connection.hset(
                        name=f"user:{user[AccountAliases.ID]}",
                        mapping=UserCash(
                            ID=user[AccountAliases.ID],
                            token=token,
                            nickname=model.nickname,
                            location_id=user[RoomAliases.ID],
                            location_rank=user.get(LocalRankAliases.rank)
                        ).model_dump(exclude_none=True)
                    )
                await socket.send(output("успешная авторизация", {"токен": token}))
        else:
            raise InternalError("пользователя не существует")


class GetOneUser(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: GetOneUserModel, token: str):
        async with engine.connect() as connection:
            cursor: CursorResult = await connection.execute(
                select(
                    accounts.c[AccountAliases.ID],
                    accounts.c[AccountAliases.nickname],
                    accounts.c[AccountAliases.created_at],
                    rooms.c[RoomAliases.ID],
                    rooms.c[RoomAliases.title]
                )
                .join(locations, locations.c[AccountAliases.ID] == accounts.c[AccountAliases.ID])
                .join(rooms, rooms.c[RoomAliases.ID] == locations.c[RoomAliases.ID], isouter=True)
                .where(accounts.c[AccountAliases.ID] == model.ID)
            )
            result: Optional[dict] = cursor.mappings().fetchone()
            if not result:
                raise InternalError("пользователь не найден")
            mess_out = GetOneUserOut(
                **{
                    AccountAliases.ID: result[AccountAliases.ID],
                    AccountAliases.nickname: result[AccountAliases.nickname],
                    AccountAliases.created_at: result[AccountAliases.created_at],
                    AccountAliases.status: AccountStatuses.ONLINE if Cash.online[
                                                                         socket.id] is not None else AccountStatuses.OFFLINE,
                    AccountAliases.location: LocationShortInfoModel(
                        **{
                            RoomAliases.ID: result[RoomAliases.ID],
                            RoomAliases.title: result[RoomAliases.title]
                        }
                    ).model_dump(by_alias=True),
                }
            )
            await socket.send(output("информация о пользователе",
                                     GetOneUserOut(**mess_out.model_dump(by_alias=True)).model_dump(by_alias=True)))


class GetOnlineUserList(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    async def get_one(self, connection: Redis, top_level_key: str):
        return await connection.hmget(top_level_key, ["ID", "nickname", "location_id"])

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: GetOnlineUserListModel, token: str):
        async with Storage() as connection:
            top_level_keys: list = await connection.keys("user:*")
            result = await asyncio.gather(*[self.get_one(connection, k) for k in top_level_keys])

            result = [{AccountAliases.ID: int(i[0]),
                       AccountAliases.nickname: i[1],
                       AccountAliases.location: None if not i[2] else int(i[2])} for i in result]
        await socket.send(output("пользователи онлайн",
                                 result
                                 ))


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
                    raise InternalError("ошибка изменения аккаунта")
            except IntegrityError as e:
                print(e)
                raise InternalError("такой ник уже существует")
        await socket.send(output("ник изменен"))
        async with Storage() as connection:
            await connection.hset(
                f"user:{user.ID}",
                "nickname",
                model.nickname
            )


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
                raise InternalError("ошибка изменения аккаунта")
        await socket.send(output("пароль изменен"))


class Relocation(BaseEvent):

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: RelocationModel, token: str):
        user: UserLink = online[socket.id]
        send_public = SendPublic("")

        async with engine.connect() as connection:
            await connection.execute(
                update(locations).values({RoomAliases.ID: model.room_id}).where(
                    locations.c[AccountAliases.ID] == user.ID)
            )
            await connection.commit()
            cursor: CursorResult = await connection.execute(
                select(local_ranks.c[LocalRankAliases.rank])
                .where(local_ranks.c[AccountAliases.ID] == user.ID)
                .where(local_ranks.c[RoomAliases.ID] == model.room_id)
            )

            rank: LocalRanks = cursor.scalar()
            cursor: CursorResult = await connection.execute(
                select(rooms.c[RoomAliases.title])
                .where(rooms.c[RoomAliases.ID == model.room_id])
            )
            target_room_title = cursor.scalar()
        async with Storage() as connection:
            location_id, nickname = await connection.hmget(
                f"user:{user.ID}",
                "location_id",
                "nickname"
            )
            if location_id:
                await send_public(socket,
                                  NewPublicModel(
                                      **{
                                          PublicAliases.text: f"[{nickname} перешел в комнату {target_room_title}]"}
                                  ),
                                  token)

                await connection.hdel(
                    f"location:{location_id}",
                    "user_id",
                    "socket_id"
                )
            await connection.hset(
                f"location:{model.room_id}",
                user.ID,
                socket.id.hex
            )
            await connection.hset(
                f"user:{user.ID}",
                mapping={"location_id": model.room_id,
                         "local_rank": rank},

            )

            # Cash.online[socket.id].local_rank = rank
            await send_public(socket,
                              NewPublicModel(
                                  **{PublicAliases.text: f"[{nickname} вошел в комнату]"}
                              ),
                              token)
