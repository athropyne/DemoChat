from dataclasses import dataclass
from enum import Enum, auto


# class RoomTypes(str, Enum):
#     OPENED = "открытая"
#     CLOSED = "звкрытая"


@dataclass
class RoomAliases:
    ID = "room_id"
    title = "title"
    owner_id = "owner_id"
    created_at = "created_at"
    # administrators = "administrators"
    # moderators = "moderators"


class LocalRanks(Enum):
    OWNER = auto()
    MODERATOR = auto()
    USER = auto()
    BANNED = auto()


@dataclass
class LocalRankAliases:
    rank = "local_rank"
