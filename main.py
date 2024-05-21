import asyncio
import inspect
from typing import List

import websockets
from pydantic import ValidationError
from websockets import WebSocketServerProtocol

import core.database
from events.exc import InternalError, NotFoundError
from core.io import InputModel, output
from core.user_cash import User, Cash
from events.inputs import input_event_mapping


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

                except ValidationError as e:
                    errors = e.errors(include_url=False, include_input=False)
                    err_output: List[str] = []
                    for i in errors:
                        if i["type"] == "missing":
                            err_output.append(f"пропущено поле '{i['loc'][0]}'")
                        elif i["type"].endswith("_type"):
                            err_output.append(f"неверный тип поля '{i['loc'][0]}'")
                        elif i["type"] == "enum":
                            err_output.append(f"поле '{i['loc'][0]}' может принимать только значения: {i['ctx']}")
                        elif i["type"] == "json_invalid":
                            err_output.append("невалидный json")
                        else:
                            err_output.append(i)

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
            if websocket.id in Cash.online:
                user = Cash.online[websocket.id]
                if user.location_id in Cash.location:
                    Cash.location[user.location_id].remove(user.socket.id)
                    if len(Cash.location[user.location_id]) == 0:
                        del Cash.location[user.location_id]
                del Cash.ids[user.ID]
                del Cash.online[websocket.id]
                del user
            print("клиент отключен")


async def main():
    await core.database.init()
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
