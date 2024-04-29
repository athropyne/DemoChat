from typing import Optional

from sqlalchemy import CursorResult, insert, select, update
from sqlalchemy.exc import IntegrityError
from websockets import WebSocketServerProtocol

from core import User
from core.base_event import BaseEvent
from core.database import engine
from core.io import InternalError, output
from core.managers import Token, PasswordManager
from core.schemas import accounts, locations, local_ranks, rooms
from core.user_cash import Cash
from services.accounts.aliases import AccountAliases, AccountStatuses
from services.accounts.models import CreateModel, AuthModel, GetOneUserOut, GetOneUserModel, GetUserListModel, \
    ChangeNickModel, RelocationModel
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
        cu: User = Cash.online[socket.id]

        cu.location_id = None
        cu.local_rank = None
        cu.nickname = model.nickname
        cu.user_id = user_id
        cu.token = token

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
            if PasswordManager.verify_hash(model.password, user[AccountAliases.password]):
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
                cu: User = Cash.online[socket.id]

                cu.location_id = user[RoomAliases.ID]
                cu.local_rank = user.get(LocalRankAliases.rank)
                cu.nickname = user[AccountAliases.nickname]
                cu.user_id = user[AccountAliases.ID]
                cu.token = token
                await socket.send(output("успешная авторизация", {"токен": token}))
        else:
            raise InternalError("пользователя не существует")


class GetOneUser(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    # @permission(Ranks.USER, update_cash=False)
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
            await socket.send(output("информация о пользователе", GetOneUserOut(**mess_out.model_dump(by_alias=True)).model_dump(by_alias=True)))


class GetUserList(BaseEvent):
    def __init__(self, name: str):
        super().__init__(name)

    # @permission(Ranks.USER, update_cash=False)
    async def __sql__call__(self, socket: WebSocketServerProtocol, model: GetUserListModel, token: str):
        stmt = select(
            accounts.c[AccountAliases.ID],
            accounts.c[AccountAliases.nickname],
            locations.c[RoomAliases.ID],
            rooms.c[RoomAliases.title]
        ) \
            .select_from(accounts) \
            .join(locations, accounts.c[AccountAliases.ID] == locations.c[AccountAliases.ID], isouter=True) \
            .join(rooms, isouter=True)

        if model.gender:
            stmt = stmt.where(accounts.c[AccountAliases.gender] == model.gender)
        if model.rank:
            stmt = stmt.where(accounts.c[AccountAliases.rank] == model.rank)
        if model.residence_place:
            stmt = stmt.where(accounts.c[AccountAliases.residence_place] == model.residence_place)
        if model.location_name:
            stmt = stmt.where(locations.c[RoomAliases.title] == model.location_name)

        async with engine.connect() as db:
            cursor: CursorResult = await db.execute(
                stmt
                .where()
                .offset(model.skip)
                .limit(model.limit)
            )

            result = cursor.mappings().fetchall()
            output = [dict(i) for i in result]
            await socket.send(Response(data=output))

    async def __call__(self, socket: WebSocketServerProtocol, model: GetUserListModel, token: str):
        ...


class ChangeNick(BaseEvent):

    @staticmethod
    async def __change_in_cash(socket: WebSocketServerProtocol, nickname: str):
        Cash.online[socket.id].set_cash(nickname=nickname)

    @staticmethod
    async def __change_in_db(socket: WebSocketServerProtocol, db, nickname: str, target_id: int):
        try:
            await db.execute(
                update(accounts).values({AccountAliases.nickname: nickname})
                .where(accounts.c[AccountAliases.ID] == target_id)
            )
            await ChangeNick.__change_in_cash(socket=socket, nickname=nickname)
            await db.commit()
        except IntegrityError:
            raise InternalError("ник уже занят")

    # @permission(Ranks.USER, update_cash=False)
    async def __call__(self, socket: WebSocketServerProtocol, model: ChangeNickModel, token: str):
        requester_id: int = Cash.online[socket.id].user_id  # ID отправившего запрос
        is_owner: bool = True if requester_id == model.ID else False

        if is_owner:
            async with engine.connect() as db:
                try:
                    await ChangeNick.__change_in_db(socket, db, model.nickname, model.ID)
                    await socket.send(
                        Response("ник успешно изменен")
                    )
                    return
                except IntegrityError:
                    raise InternalError("ник уже занят")
        else:
            requester = accounts.alias("инициатор")
            target = accounts.alias("цель")
            async with engine.connect() as db:
                cursor: CursorResult = await db.execute(
                    select(
                        requester.c[AccountAliases.rank].label("ранг инициатора"),
                        target.c[AccountAliases.rank].label("ранг цели")
                    )
                    .where(requester.c[AccountAliases.ID] == requester_id)
                    .where(target.c[AccountAliases.ID] == model.ID)
                )

                result: Optional[dict] = cursor.mappings().fetchone()

                if not result:
                    raise InternalError("пользователя не существует")
                result = dict(result)
                if permissions[result["ранг инициатора"]] > permissions[result["ранг цели"]]:
                    try:
                        await ChangeNick.__change_in_db(socket, db, model.nickname, model.ID)
                        await socket.send(
                            Response("ник успешно изменен")
                        )
                        return
                    except IntegrityError:
                        raise InternalError("ник уже занят")
                else:
                    raise InternalError("недостаточно прав")


class Relocation(BaseEvent):

    # @permission(Ranks.USER, update_cash=False)
    async def __call__(self, socket: WebSocketServerProtocol, model: RelocationModel, token: str):
        user: User = Cash.online[socket.id]
        send_public = SendPublic("")

        async with engine.connect() as db:
            await db.execute(
                update(locations).values({RoomAliases.ID: model.room_id}).where(
                    locations.c[AccountAliases.ID] == user.user_id)
            )
            cursor: CursorResult = await db.execute(
                select(local_ranks.c[LocalRankAliases.rank])
                .where(local_ranks.c[AccountAliases.ID] == user.user_id)
                .where(local_ranks.c[RoomAliases.ID] == model.room_id)
            )
            rank: LocalRanks = cursor.scalar()
            await db.commit()
            cursor: CursorResult = await db.execute(
                select(rooms.c[RoomAliases.title])
                .where(rooms.c[RoomAliases.ID == model.room_id])
            )
            target_room_title = cursor.scalar()
        if user.location_id:
            await send_public(socket,
                              NewPublicModel(
                                  **{
                                      PublicAliases.text: f"[перешел в комнату {target_room_title}]"}
                              ),
                              token)
        user.location_id = model.room_id
        Cash.online[socket.id].local_rank = rank
        await send_public(socket,
                          NewPublicModel(
                              **{PublicAliases.text: f"[{Cash.online[socket.id].nickname} вошел в комнату]"}
                          ),
                          token)
