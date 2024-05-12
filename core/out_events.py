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
                       *sockets: WebSocketServerProtocol,
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
        super().__init__("success")


class NewToken(BaseOutEvent):

    def __init__(self):
        super().__init__("new_token")


class OneUserInfo(BaseOutEvent):

    def __init__(self):
        super().__init__("user_info")


class OnlineUserListInfo(BaseOutEvent):

    def __init__(self):
        super().__init__("online_list")


class SystemMessage(BaseOutEvent):
    def __init__(self):
        super().__init__("system")
