from typing import Optional

from core.io import IO_TYPE, Error


class InternalError(Exception):
    def __init__(self, error: str, payload: Optional[IO_TYPE] = None):
        self.error = Error(
            error=error,
            payload=payload
        )

    def __call__(self):
        return self.error.model_dump_json(by_alias=True)


class AccessDenied(InternalError):
    def __init__(self, data: Optional[IO_TYPE]):
        super().__init__("доступ запрещен", data)


class NonAuthorized(InternalError):
    def __init__(self):
        super().__init__("вы не авторизованы")


class DuplicateError(InternalError):
    def __init__(self, data: Optional[IO_TYPE]):
        super().__init__("дубль", data)


class InvalidDataError(InternalError):
    def __init__(self, data: Optional[IO_TYPE]):
        super().__init__("неверные данные", data)


class NotFoundError(InternalError):
    def __init__(self, data: Optional[IO_TYPE]):
        super().__init__("не найдено", data)


class UpdateError(InternalError):
    def __init__(self, data: Optional[IO_TYPE]):
        super().__init__("не обновлено", data)
