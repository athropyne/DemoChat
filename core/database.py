from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.config import SQLITE_URL, PG_URL
from core.schemas import metadata, rooms
from services.rooms.aliases import RoomAliases

engine: AsyncEngine = create_async_engine(PG_URL, echo=True)


async def init():
    async with engine.connect() as connection:
        await connection.run_sync(metadata.drop_all)
        await connection.run_sync(metadata.create_all)
        await connection.execute(
            insert(rooms).values({RoomAliases.title: "главная"})
        )
        await connection.commit()
