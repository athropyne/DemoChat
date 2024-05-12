from typing import Optional

from core.io import IO_TYPE
from services.accounts.events import Create, Auth, GetOneUser, GetOnlineUserList, ChangeNick, Relocation
from services.messages.events import SendPublic
from services.rooms.events import CreateRoom, UpdatePermission

in_events = [
    Create("signup"),
    Auth("signin"),
    GetOneUser("get one user"),
    GetOnlineUserList("online list"),
    ChangeNick("change nickname"),
    Relocation("relocate"),
    CreateRoom("create room"),
    SendPublic("send public"),
    UpdatePermission("update permission")
]

out_events = [

]



