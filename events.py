from typing import Optional

from core.io import IO_TYPE
from services.accounts.events import Create, Auth, GetOneUser, GetOnlineUserList, ChangeNick, Relocation
from services.messages.events import SendPublic
from services.rooms.events import CreateRoom, UpdatePermission

in_events = [
    Create("зарегистрироваться"),
    Auth("залогиниться"),
    GetOneUser("получить пользователя"),
    GetOnlineUserList("кто онлайн"),
    ChangeNick("изменить ник"),
    Relocation("войти в комнату"),
    CreateRoom("создать комнату"),
    SendPublic("написать в комнату"),
    UpdatePermission("изменить привелегии")
]

out_events = [

]



