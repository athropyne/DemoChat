from services.accounts.events import Create, Auth, GetOneUser, GetUserList, ChangeNick, Relocation
from services.messages.events import SendPublic
from services.rooms.events import CreateRoom

events = [
    Create("зарегистрироваться"),
    Auth("залогиниться"),
    GetOneUser("получить пользователя"),
    GetUserList("получить список пользователей"),
    ChangeNick("изменить ник"),
    Relocation("войти в комнату"),
    CreateRoom("создать комнату"),
    SendPublic("написать в комнату")
]
