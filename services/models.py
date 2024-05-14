from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class PaginatorAliases:
    SKIP = "skip"
    LIMIT = "limit"


class Paginator(BaseModel):
    skip: int = Field(0, alias=PaginatorAliases.SKIP)
    limit: int = Field(50, alias=PaginatorAliases.LIMIT)
