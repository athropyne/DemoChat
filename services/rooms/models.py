from typing import Optional

from pydantic import BaseModel, Field

from services.accounts.aliases import AccountAliases
from services.rooms.aliases import RoomAliases, LocalRanks, LocalRankAliases


class CreateRoomModel(BaseModel):
    title: str = Field(alias=RoomAliases.title, max_length=24)


class LocationShortInfoModel(BaseModel):
    id: Optional[int] = Field(alias=RoomAliases.ID)
    title: Optional[str] = Field(alias=RoomAliases.title)


class AddLocalPermissionModel(BaseModel):
    target_user_id: int = Field(alias=AccountAliases.ID)
    rank: LocalRanks = Field(alias=LocalRankAliases.rank)


class RemoveLocalPermissionModel(BaseModel):
    target_user_id: int = Field(alias=AccountAliases.ID)


local_rank_level = {
    LocalRanks.BANNED: 0,
    LocalRanks.USER: 1,
    LocalRanks.MODERATOR: 2,
    LocalRanks.OWNER: 3,
}



