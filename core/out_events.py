from abc import ABC, abstractmethod
from typing import Optional, Type, List, Union, Set

from pydantic import BaseModel
from websockets import WebSocketServerProtocol

from core.base_event import BaseEvent
from core.io import IO_TYPE, OutputModel


class BaseOutEvent(ABC):
    @abstractmethod
    def __init__(self, name: str):
        self.name = name

    async def __call__(self,
                       sockets: Set[WebSocketServerProtocol],
                       model: Optional[Union[BaseModel, IO_TYPE]] = None,
                       token: Optional[str] = None):
        payload = model
        if isinstance(model, BaseModel):
            payload = model.model_dump(by_alias=True)
        output = OutputModel(event=self.name,
                             payload=payload,
                             token=token
                             ).model_dump_json(by_alias=True, exclude_none=True)
        for s in sockets:
            await s.send(output)


class Successfully(BaseOutEvent):
    def __init__(self):
        super().__init__("успех")


class OneUserInfo(BaseOutEvent):

    def __init__(self):
        super().__init__("информация о пользователе")


class OnlineUserListInfo(BaseOutEvent):

    def __init__(self):
        super().__init__("пользователи онлайн")

class SystemMessage(BaseOutEvent):
    def __init__(self):
        super().__init__("системное сообщение")