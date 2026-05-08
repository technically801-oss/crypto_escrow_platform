from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db, AsyncSessionLocal
from app.models import ServiceCategory
from app.web.routes import router as web_router
from app.bot.bot import start_bot
from app.services.notification_service import start_scheduler
from sqlalchemy import select

DEFAULT_SERVICES = ['Website Development', 'Telegram Bot', 'Crypto Project', 'Trading Bot', 'Roblox Game', 'Mobile App']

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        for name in DEFAULT_SERVICES:
            exists = await session.scalar(select(ServiceCategory).where(ServiceCategory.name == name))
            if not exists:
                session.add(ServiceCategory(name=name))
        await session.commit()
    await start_bot()
    start_scheduler()
    yield

app = FastAPI(title='Crypto Escrow Freelancer Platform', lifespan=lifespan)
app.mount('/static', StaticFiles(directory='app/static'), name='static')
app.include_router(web_router)

@app.get('/health')
async def health():
    return {'status': 'ok'}
