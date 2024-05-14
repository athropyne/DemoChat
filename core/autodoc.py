from pprint import pprint
from typing import Optional, Dict, Union, List
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.json_schema import GenerateJsonSchema, models_json_schema


class User(BaseModel):
    name: str = Field(max_length=15, title="nickname", description="nickname field")
    age: Union[int, List[UUID]] = 15


class OOO(BaseModel):
    __title__ = "общество с ограниченной ответственностью"
    user: User
    organization_name: str
    class Config:
        NAME = "общество с ограниченной ответственностью"

pprint(OOO.__fields__['user'].annotation)

# pprint(models_json_schema([(OOO,'serialization'), (User,'serialization')]))
