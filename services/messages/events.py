import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import CursorResult, insert
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.database import engine
from core.exc import AccessDenied
from core.io import output
from core.schemas import public
from core.security import protected
from core.user_cash import Cash, User
from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.messages.models import NewPublicModel, PublicMessageOut, Author
from services.rooms.aliases import LocalRankAliases, LocalRanks


class  SendPublic(BaseEvent):

    @protected
    def __init__(self, socket: WebSocketServerProtocol, model: NewPublicModel, token: Optional[str]):
        super().__init__(socket, model, token)

    async def __call__(self):
        user: User = Cash.online[self.socket.id]

        if user.local_rank is LocalRanks.BANNED:
            raise AccessDenied("вы в бане. парьтесь :)")
        data = {
            PublicAliases.creator: user.ID,
            PublicAliases.room: user.location_id,
            PublicAliases.text: self.model.text
        }
        message_out = PublicMessageOut(
            **{
                PublicAliases.text: self.model.text,
                PublicAliases.created_at: datetime.datetime.utcnow(),
                PublicAliases.creator: Author(
                    **{
                        AccountAliases.ID: user.ID,
                        AccountAliases.nickname: user.nickname,
                        LocalRankAliases.rank: user.local_rank
                    }
                )
            }
        )
        for socket_id in Cash.location[user.location_id]:
            await Cash.online[socket_id].socket.send(output("новое сообщение", message_out.model_dump(by_alias=True)))
        async with engine.connect() as db:
            cursor: CursorResult = await db.execute(
                insert(public).values(data)
            )
            await db.commit()

