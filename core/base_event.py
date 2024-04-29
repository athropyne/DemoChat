from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel
from websockets import WebSocketServerProtocol


class BaseEvent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def __call__(self, socket: WebSocketServerProtocol, model: Type[BaseModel], token: str):
        pass
