import datetime

from sqlalchemy import CursorResult, insert
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.io import output
from core.schemas import public
from core.user_cash import User, Cash
from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.messages.models import NewPublicModel, PublicMessageOut, Author
from services.rooms.aliases import LocalRankAliases


class SendPublic(BaseEvent):

    # @permission(Ranks.USER, update_cash=False)
    async def __call__(self, socket: WebSocketServerProtocol, model: NewPublicModel, token: str):
        user: User = Cash.online[socket.id]
        data = {
            PublicAliases.creator: user.user_id,
            PublicAliases.room: user.location_id,
            PublicAliases.text: model.text
        }
        message_out = PublicMessageOut(
            **{
                PublicAliases.text: model.text,
                PublicAliases.created_at: datetime.datetime.utcnow(),
                PublicAliases.creator: Author(
                    **{
                        AccountAliases.ID: Cash.online[socket.id].user_id,
                        AccountAliases.nickname: Cash.online[socket.id].nickname,
                        LocalRankAliases.rank: Cash.online[socket.id].local_rank
                    }
                )
            }
        )
        for local_user in Cash.channels[user.location_id]:
            await local_user.socket.send(output("новое сообщение", message_out.model_dump(by_alias=True)))
        async with engine.connect() as db:
            cursor: CursorResult = await db.execute(
                insert(public).values(data)
            )
            await db.commit()

