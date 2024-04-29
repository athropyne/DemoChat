import asyncio
import inspect
from typing import Optional, Callable, Type

import events
import websockets
from pydantic import BaseModel
from websockets import WebSocketServerProtocol

import core.database
from core.io import InputModel, output
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
    async for message in websocket:
        # try:
        #     try:
                data = InputModel.model_validate_json(message)
                callback: Callable = events_mapping[data.event]
                model: Type[BaseModel] = inspect.signature(callback).parameters['model'].annotation
                token: Optional[str] = data.token
                await callback(websocket, model(**data.payload), token)
        #     except ValidationError as e:
        #         errors = e.errors(include_url=False, include_input=False)
        #         err_output: List[str] = []
        #         for i in errors:
        #             if i["type"] == "missing":
        #                 err_output.append(f"пропущено поле '{i['loc'][0]}'")
        #             elif i["type"] == "string_type":
        #                 err_output.append(f"поле '{i['loc'][0]}' должно быть строкой")
        #             elif i["type"] == "json_invalid":
        #                 err_output.append(f"невалидный json")
        #             elif i["type"] == "dict_type":
        #                 err_output.append(f"поле '{i['loc'][0]}' должно быть объектом json")
        #             else:
        #                 err_output.append("ошибка анализа данных")
        #         raise InternalError(-1, err_output)
        #     except Exception as e:
        #         raise InternalError(-1, str(e))
        # except InternalError as e:
        #     await websocket.send((e()))

    # except websockets.exceptions.ConnectionClosed:
    #     user_id = None
    #     async for token_storage in get_redis(RedisStorageTypes.TOKEN):
    #         user_id = await token_storage.get(sockets[websocket.id])
    #     async for user_storage in get_redis(RedisStorageTypes.USER):
    #         await user_storage.delete(user_id)


async def main():
    await core.database.init()
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())

