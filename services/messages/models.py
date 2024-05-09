import datetime
from typing import Union, Optional

from pydantic import BaseModel, Field

from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.rooms.aliases import LocalRanks, LocalRankAliases


class NewPublicModel(BaseModel):
    text: str = Field(alias=PublicAliases.text, max_length=256)


class Author(BaseModel):
    user_id: int = Field(serialization_alias=AccountAliases.ID)
    nickname: str = Field(serialization_alias=AccountAliases.nickname)
    local_rank: Optional[LocalRanks] = Field(serialization_alias=LocalRankAliases.rank)


class PublicMessageOut(BaseModel):
    text: str = Field(serialization_alias=PublicAliases.text, max_length=256)
    author: Author = Field(serialization_alias=PublicAliases.creator)
    created_at: datetime.datetime = Field(serialization_alias=PublicAliases.created_at,
                                          default_factory=datetime.datetime.now)



