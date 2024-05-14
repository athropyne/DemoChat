import inspect
from pprint import pprint

from pydantic import BaseModel

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

# with open("doc.md", "w+", encoding="utf-8", newline="\n") as f:
#     res_strings = []
#     for k, v in input_event_mapping.items():
#         model: BaseModel = inspect.signature(v.__init__).parameters['model'].annotation
#         payload: dict = model.model_json_schema()
#         event_description = v.__doc__
#         event_name = k
#         required = []
#         if req := payload.get('required'):
#             required = req
#
#         for param, props in payload["properties"].items():
#             ...
#             if 'type' in props:
#                 param_type = props['type']
#             if 'maxLength' in props:
#                 max_length = props['maxLength']
#
#             f.write(f"## {v.__doc__}\n")
#             # res_strings.append(v.__doc__)
#             f.write(f"### событие '***{k}***' \n")
#             f.write(f"#### параметры \n")
#
#         schema = {
#             "@": k,
#             "#": payload,
#             # "$": None
#         }
#         pprint(schema)
#         print()
#     # res_strings.append(schema)

# pprint(res_strings)
