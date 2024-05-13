from dataclasses import dataclass
from enum import Enum


@dataclass
class RoomAliases:
    ID = "room_id"
    title = "title"
    owner_id = "owner_id"
    created_at = "created_at"


class LocalRanks(str, Enum):
    OWNER = "owner"
    MODERATOR = "moderator"
    USER = "user"
    BANNED = "banned"


@dataclass
class LocalRankAliases:
    rank = "local_rank"
