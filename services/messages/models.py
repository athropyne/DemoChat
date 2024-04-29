import datetime
from typing import Union, Optional

from pydantic import BaseModel, Field

from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.rooms.aliases import LocalRanks, LocalRankAliases


class NewPublicModel(BaseModel):
    text: str = Field(alias=PublicAliases.text, max_length=256)


class Author(BaseModel):
    user_id: int = Field(alias=AccountAliases.ID)
    nickname: str = Field(alias=AccountAliases.nickname)
    local_rank: Optional[LocalRanks] = Field(alias=LocalRankAliases.rank)


class PublicMessageOut(BaseModel):
    text: str = Field(alias=PublicAliases.text, max_length=256)
    author: Author = Field(alias=PublicAliases.creator)
    created_at: datetime.datetime = Field(alias=PublicAliases.created_at)



