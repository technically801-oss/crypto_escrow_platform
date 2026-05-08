from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Project, User
from app.bot.bot import bot

scheduler = AsyncIOScheduler()

async def reminder_job():
    if bot is None:
        return
    async with AsyncSessionLocal() as session:
        projects = (await session.scalars(select(Project).where(Project.status.in_(['In Progress', 'Submitted', 'Revision'])))).all()
        now = datetime.utcnow()
        for p in projects:
            if p.paused:
                continue
            seller = await session.get(User, p.seller_id) if p.seller_id else None
            client = await session.get(User, p.client_id) if p.client_id else None
            if p.status == 'In Progress' and seller and seller.telegram_id:
                await bot.send_message(seller.telegram_id, f'Reminder: Project #{p.id} is pending. Deadline: {p.deadline_at}')
            if p.status == 'Submitted' and p.submitted_at and client and client.telegram_id:
                review_deadline = p.submitted_at + timedelta(days=settings.auto_release_days)
                if now >= review_deadline:
                    # auto-release handled by admin manual in simple starter; notify admin/client
                    await bot.send_message(client.telegram_id, f'Project #{p.id} delivery review period expired. It may be auto-released/admin reviewed.')


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(reminder_job, 'interval', hours=settings.reminder_hours, id='reminders', replace_existing=True)
        scheduler.start()
