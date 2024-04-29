from typing import Union, Optional

from pydantic import BaseModel, Field

from services.rooms.aliases import RoomAliases


class CreateRoomModel(BaseModel):
    title: str = Field(alias=RoomAliases.title, max_length=24)


class LocationShortInfoModel(BaseModel):
    id: Optional[int] = Field(alias=RoomAliases.ID)
    title: Optional[str] = Field(alias=RoomAliases.title)
