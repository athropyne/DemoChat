import datetime
from uuid import UUID

from sqlalchemy import CursorResult, insert
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.io import output, InternalError
from core.schemas import public
from core.security import protected
from core.user_cash import Storage, online
from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.messages.models import NewPublicModel, PublicMessageOut, Author
from services.rooms.aliases import LocalRankAliases, LocalRanks


class SendPublic(BaseEvent):

    @protected
    async def __call__(self, socket: WebSocketServerProtocol, model: NewPublicModel, token: str):
        user_id: int = online[socket.id].ID
        async with Storage() as connection:
            location_id, local_rank, nickname = await connection.hmget(
                f"user:{user_id}",
                "location_id",
                "local_rank",
                "nickname"
            )
            # print(location_id, local_rank, nickname)
            users_in_room: dict = await connection.hgetall(
                f"location:{location_id}"
            )
            # print(users_in_room)
        if local_rank is LocalRanks.BANNED:
            raise InternalError("операция недоступна", "вы в бане. парьтесь :)")
        data = {
            PublicAliases.creator: user_id,
            PublicAliases.room: location_id,
            PublicAliases.text: model.text
        }
        message_out = PublicMessageOut(
            **{
                PublicAliases.text: model.text,
                PublicAliases.created_at: datetime.datetime.utcnow(),
                PublicAliases.creator: Author(
                    **{
                        AccountAliases.ID: user_id,
                        AccountAliases.nickname: nickname,
                        LocalRankAliases.rank: local_rank
                    }
                )
            }
        )
        for i in online:
            print(i)
        for socket_id in users_in_room.values():
            await online[UUID(socket_id)].socket.send(output("новое сообщение", message_out.model_dump(by_alias=True)))
        async with engine.connect() as db:
            cursor: CursorResult = await db.execute(
                insert(public).values(data)
            )
            await db.commit()

