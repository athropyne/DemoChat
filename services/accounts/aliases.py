from dataclasses import dataclass
from enum import Enum


@dataclass
class AccountAliases:
    ID = "user_id"
    nickname = "nickname"
    password = "password"
    created_at = "created_at"
    location = "location"
    status = "status"


class AccountStatuses(str, Enum):
    ONLINE = "online"
    OFFLINE = "ofline"
