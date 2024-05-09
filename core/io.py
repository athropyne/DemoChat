from __future__ import annotations

from enum import Enum
from typing import Union, Optional, Any

from pydantic import BaseModel, Field

from core.codes import output_code

IO_TYPE = Union[str, dict, list]


class InputModel(BaseModel):
    event: str = Field(alias="@")
    payload: IO_TYPE = Field(alias="#")
    token: Optional[str] = Field(None, alias="$")


class OutputModel(InputModel):
    event: str = Field(serialization_alias="@")
    payload: Optional[IO_TYPE] = Field(serialization_alias="#")
    # request_command: Optional[str] = Field(None, serialization_alias="$")


def output(event: str, payload: Optional[IO_TYPE] = None):
    return OutputModel(
        event=event,
        payload=payload
    ).model_dump_json(by_alias=True)


class Error(BaseModel):
    error: str = Field(serialization_alias="!")
    payload: Optional[IO_TYPE] = Field(serialization_alias="#")



