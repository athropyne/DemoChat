from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.config import SQLITE_URL, PG_URL
from core.schemas import metadata

engine: AsyncEngine = create_async_engine(PG_URL, echo=True)


async def init():
    async with engine.connect() as connection:
        await connection.run_sync(metadata.drop_all)
        await connection.run_sync(metadata.create_all)
        await connection.commit()
