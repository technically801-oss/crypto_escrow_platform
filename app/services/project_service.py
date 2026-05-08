from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import Project, User, Payment, ProjectMessage, Withdrawal, Refund, Rating, Delivery, Dispute

async def get_or_create_user(session: AsyncSession, telegram_id: int | None = None, username: str | None = None, full_name: str | None = None, role: str = 'client') -> User:
    user = None
    if telegram_id:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user and username:
        user = await session.scalar(select(User).where(User.telegram_username == username.lstrip('@')))
    if not user:
        user = User(telegram_id=telegram_id, telegram_username=(username or '').lstrip('@') or None, full_name=full_name, role=role)
        session.add(user)
    else:
        if telegram_id and not user.telegram_id:
            user.telegram_id = telegram_id
        if username and not user.telegram_username:
            user.telegram_username = username.lstrip('@')
    await session.commit()
    return user

async def add_message(session: AsyncSession, project_id: int, message: str, user_id: int | None = None):
    session.add(ProjectMessage(project_id=project_id, message=message, user_id=user_id))
    await session.commit()

async def create_payment(session: AsyncSession, project: Project, coin: str, wallet: str) -> Payment:
    amount_due = project.budget * (1 + settings.platform_client_fee_percent / 100)
    payment = Payment(project_id=project.id, coin=coin, amount_due=amount_due, wallet_address=wallet)
    project.payment_status = 'Pending'
    session.add(payment)
    await session.commit()
    return payment

async def release_seller_funds(session: AsyncSession, project: Project):
    seller = await session.get(User, project.seller_id)
    if not seller:
        return
    seller_amount = project.budget * (1 - settings.platform_seller_fee_percent / 100)
    seller.balance += seller_amount
    project.status = 'Completed'
    project.payment_status = 'Released'
    project.approved_at = datetime.utcnow()
    await session.commit()
