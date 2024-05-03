import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field

from services.accounts.aliases import AccountAliases, AccountStatuses
from services.models import Paginator
from services.rooms.aliases import RoomAliases
from services.rooms.models import LocationShortInfoModel


class AuthModel(BaseModel):
    nickname: str = Field(alias=AccountAliases.nickname, max_length=16)
    password: str = Field(alias=AccountAliases.password, max_length=36)


class CreateModel(AuthModel):
    ...


class AuthModelOut(BaseModel):
    token: str = Field(serialization_alias="токен")


class GetOneUserModel(BaseModel):
    ID: int = Field(alias=AccountAliases.ID)


class GetOneUserOutProjection(BaseModel):
    id: int = Field(alias=AccountAliases.ID)
    nickname: str = Field(alias=AccountAliases.nickname, max_length=16)
    created_at: datetime.date = Field(alias=AccountAliases.created_at, default_factory=datetime.date.today)
    location: LocationShortInfoModel = Field(alias=AccountAliases.location)


class GetOneUserOut(GetOneUserOutProjection):
    status: AccountStatuses = Field(alias=AccountAliases.status)


@dataclass
class Error:
    USER_NOT_FOUND = "пользователь не найден"


class GetOnlineUserListModel(Paginator):
    location_id: Optional[int] = Field(None, alias=RoomAliases.ID)
    location_name: Optional[str] = Field(None, alias=RoomAliases.title, max_length=24)


class GetUserListOut(BaseModel):
    ID: int = Field(alias=AccountAliases.ID)
    nickname: str = Field(alias=AccountAliases.nickname),
    location_id: int = Field(alias=RoomAliases.ID)
    location_name: str = Field(alias=RoomAliases.title)


class ChangeNickModel(BaseModel):
    nickname: str = Field(alias=AccountAliases.nickname)


class ChangePasswordModel(BaseModel):
    password: str = Field(alias=AccountAliases.password)


class RelocationModel(BaseModel):
    room_id: int = Field(alias=RoomAliases.ID)
