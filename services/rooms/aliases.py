from dataclasses import dataclass
from enum import Enum


class RoomTypes(str, Enum):
    OPENED = "открытая"
    CLOSED = "звкрытая"


@dataclass
class RoomAliases:
    ID = "идентификатор комнаты"
    title = "название"
    type = "тип"
    owner_id = "идентификатор хозяина"
    created_at = "дата создания"
    administrators = "администраторы"
    moderators = "модераторы"

class LocalRanks(str, Enum):
    OWNER = "хозяин"
    MODERATOR = "модератор"
    BANNED = "забанен"


@dataclass
class LocalRankAliases:
    rank = "локальный ранг"
