from dataclasses import dataclass


@dataclass
class PublicAliases:
    ID = "идентификатор сообщения"
    creator = "автор"
    room = "локация"
    text = "текст"
    created_at = "дата создания"



@dataclass
class PublicOutAliases:
    TEXT = "текст"
    USER = "автор"
    ROOM_ID = "комната"


class PrivateAliases:
    ID = "идентификатор сообщения"
    creator_id = "идентификатор автора"
    target_id = "идентификатор получателя"
    text = "текст"
    created_at = "дата создания"
