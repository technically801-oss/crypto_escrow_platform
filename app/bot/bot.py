import asyncio
from aiogram import Bot, Dispatcher
from app.config import settings
from app.bot.handlers import router

bot: Bot | None = None
dp: Dispatcher | None = None

async def start_bot():
    global bot, dp
    if not settings.bot_token:
        print('BOT_TOKEN not set; bot not started')
        return
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    print('Telegram bot polling started')
