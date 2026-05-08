from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

connect_args = {}
if settings.db_url.startswith('sqlite'):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(settings.db_url, echo=False, future=True, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from app import models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
