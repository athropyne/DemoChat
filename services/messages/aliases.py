from dataclasses import dataclass


@dataclass
class PublicAliases:
    ID = "message_id"
    creator = "creator"
    room = "room_id"
    text = "text"
    created_at = "created_at"
