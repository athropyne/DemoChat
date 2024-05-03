import asyncio
import inspect
from typing import Optional, Callable, Type, List

import events
import websockets
from pydantic import BaseModel, ValidationError
from websockets import WebSocketServerProtocol

import core.database
from core.io import InputModel, output, InternalError
from core.user_cash import User, Cash

events_mapping = {
    event.name: event.__call__
    for event
    in events.events
}


async def handler(websocket: WebSocketServerProtocol):
    Cash.online[websocket.id] = User(socket=websocket)  # запомнили подключение
    await websocket.send(output("успешное подключение"))
    websocket.ping_interval = 5
    while True:
        try:
            try:
                try:
                    message = await websocket.recv()
                    data = InputModel.model_validate_json(message)
                    callback: Callable = events_mapping[data.event]
                    model: Type[BaseModel] = inspect.signature(callback).parameters['model'].annotation
                    token: Optional[str] = data.token
                    await callback(websocket, model(**data.payload), token)
                    print(Cash.online.get(websocket.id))
                    print(Cash.channels)
                    print(Cash.ids)
                except ValidationError as e:
                    print(e.__traceback__)
                    errors = e.errors(include_url=False, include_input=False)
                    err_output: List[str] = []
                    for i in errors:
                        if i["type"] == "missing":
                            err_output.append(f"пропущено поле '{i['loc'][0]}'")
                        elif i["type"] == "string_type":
                            err_output.append(f"поле '{i['loc'][0]}' должно быть строкой")
                        elif i["type"] == "json_invalid":
                            err_output.append(f"невалидный json")
                        elif i["type"] == "dict_type":
                            err_output.append(f"поле '{i['loc'][0]}' должно быть объектом json")
                        else:
                            err_output.append("ошибка анализа данных")
                    raise InternalError("ошибка",err_output)
                except Exception as e:
                    # print(e.__traceback__.tb_lineno)
                    raise InternalError(str(e))
            except InternalError as e:
                # print(e.__traceback__.tb_lineno)
                await websocket.send((e()))

        except websockets.exceptions.ConnectionClosed:
            if Cash.online[websocket.id].location_id in Cash.channels:
                del Cash.channels[Cash.online[websocket.id].location_id]
            if Cash.ids.get(Cash.online[websocket.id].user_id) is not None:
                del Cash.ids[Cash.online[websocket.id].user_id]
            del Cash.online[websocket.id]
            print("END")
            print(Cash.online)
            print(Cash.channels)
            print(Cash.ids)
            break

async def main():
    await core.database.init()
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())

