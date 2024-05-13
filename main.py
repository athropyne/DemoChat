import asyncio
import inspect
from traceback import print_tb
from typing import Optional, Callable, Type, List

import websockets
from pydantic import BaseModel, ValidationError
from websockets import WebSocketServerProtocol

import core.database
import events
from core.exc import InternalError, NotFoundError
from core.io import InputModel, output
from core.user_cash import online, User, Cash
from events import input_event_mapping
from services.accounts.events import GetOnlineUserList
from services.accounts.models import GetOnlineUserListModel


# events_mapping = {
#     event.name: event.__call__
#     for event
#     in events.in_events
# }


async def handler(websocket: WebSocketServerProtocol):
    Cash.online[websocket.id] = User(socket=websocket)  # запомнили подключение
    await websocket.send(output("успешное подключение"))
    while True:
        try:
            try:
                try:
                    message = await websocket.recv()
                    data = InputModel.model_validate_json(message)
                    event = input_event_mapping.get(data.event)
                    if event is None:
                        raise NotFoundError("такой команды не существует")
                    model = inspect.signature(event.__init__).parameters['model'].annotation
                    await event(websocket, model(**data.payload), data.token)()
                    for sid, user in Cash.online.items():
                        print(f"{sid=}")
                        print(f"{user.ID=}")
                        print(f"{user.nickname=}")
                        print(f"{user.location_id=}")
                        print(f"{user.local_rank=}")
                        # print(f"{Cash.ids[user.ID]=}")
                    print()
                    for rid, sid in Cash.location.items():
                        print(f"{rid=}")
                        print(f"{sid}")
                    print()

                except ValidationError as e:
                    print_tb(e.__traceback__)
                    errors = e.errors(include_url=False, include_input=False)
                    err_output: List[str] = []
                    print(errors)
                    for i in errors:
                        if i["type"] == "missing":
                            err_output.append(f"пропущено поле '{i['loc'][0]}'")
                        if i["type"].endswith("_type"):
                            err_output.append(f"неверный тип поля '{i['loc'][0]}'")
                        if i["type"] == "json_invalid":
                            err_output.append("невалидный json")
                    if err_output:
                        raise InternalError("ошибка валидации", err_output)
                # except Exception as e:
                #     if isinstance(e, InternalError):
                #         raise e
                #     else:
                #         print_tb(e.__traceback__)
                #         print(e.args)
                #         raise InternalError("внутренняя ошибка")
            except InternalError as e:
                await websocket.send(e())
        except websockets.exceptions.WebSocketException:
            user = Cash.online[websocket.id]
            Cash.location[user.location_id].remove(user.socket.id)
            if len(Cash.location[user.location_id]) == 0:
                del Cash.location[user.location_id]
            del Cash.ids[user.ID]
            del Cash.online[websocket.id]
            del user
            print("клиент отключен")
            for sid, user in Cash.online.items():
                print(f"{sid=}")
                print(f"{user.ID=}")
                print(f"{user.nickname=}")
                print(f"{user.location_id=}")
                print(f"{user.local_rank=}")
                # print(f"{Cash.ids[user.ID]=}")
            print()
            for rid, sid in Cash.location.items():
                print(f"{rid=}")
                print(f"{sid}")
            print()
            break



async def main():
    await core.database.init()
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
