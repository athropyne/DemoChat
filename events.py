from typing import Optional

from core.io import IO_TYPE
from services.accounts.events import Create, Auth, GetOneUser, GetOnlineUserList, ChangeNick, Relocation, ChangePassword
from services.messages.events import SendPublic
from services.rooms.events import CreateRoom, UpdatePermission, GetOnlineRoomList

input_event_mapping = {
    "signup": Create,
    "signin": Auth,
    "get one user": GetOneUser,
    "online list": GetOnlineUserList,
    "change nickname": ChangeNick,
    "change password": ChangePassword,
    "relocate": Relocation,
    "create room": CreateRoom,
    "online room list": GetOnlineRoomList,
    "send public": SendPublic,
    "update permission": UpdatePermission

}

in_events = [
    # Create("signup"),
    # Auth("signin"),
    # GetOneUser("get one user"),
    # GetOnlineUserList("online list"),
    # ChangeNick("change nickname"),
    # Relocation("relocate"),
    # CreateRoom("create room"),
    # SendPublic("send public"),
    # UpdatePermission("update permission")
]

out_events = [

]
