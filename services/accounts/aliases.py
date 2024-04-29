from dataclasses import dataclass
from enum import Enum


@dataclass
class AccountAliases:
    ID = "идентификатор пользователя"
    nickname = "ник"
    password = "пароль"
    created_at = "дата регистрации"
    location = "локация"
    status = "статус"


class AccountStatuses(str,Enum):
    ONLINE = "онлайн"
    OFFLINE = "оффлайн"
