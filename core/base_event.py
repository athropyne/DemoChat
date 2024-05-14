from abc import ABC, abstractmethod
from typing import Optional

from websockets import WebSocketServerProtocol


class BaseEvent(ABC):
    @abstractmethod
    def __init__(self, socket: WebSocketServerProtocol, model, token: Optional[str]):
        self.socket = socket
        self.model = model
        self.token = token

    @abstractmethod
    async def __call__(self):
        pass
