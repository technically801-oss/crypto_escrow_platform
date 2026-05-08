from datetime import datetime, timedelta
import io
import qrcode
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Project, User, Payment, Delivery, Dispute, Withdrawal, Refund, Rating
from app.services.project_service import get_or_create_user, create_payment, release_seller_funds, add_message
from app.bot.keyboards import main_menu, seller_offer, payment_button, coins, client_review, seller_project, admin_project

router = Router()
STATE: dict[int, tuple[str, int | None]] = {}

def is_admin(tg_id: int) -> bool:
    return tg_id in settings.admin_ids

async def notify_admins(bot: Bot, text: str, project_id: int | None = None):
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=admin_project(project_id) if project_id else None)
        except Exception:
            pass

@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    args = (message.text or '').split(maxsplit=1)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
        if len(args) > 1 and args[1].startswith('project_'):
            pid = int(args[1].replace('project_', ''))
            project = await session.get(Project, pid)
            if project:
                if project.seller_telegram_username and project.seller_telegram_username.lower() == (message.from_user.username or '').lower():
                    project.seller_id = user.id
                    user.role = 'seller'
                    await session.commit()
                    await message.answer(f"New project offer #{project.id}\nType: {project.project_type}\nBudget: ${project.budget}\nTimeline: {project.timeline_days} days\n\n{project.description}", reply_markup=seller_offer(project.id))
                    return
                project.client_id = user.id if not project.client_id else project.client_id
                await session.commit()
                await message.answer(f"Project #{project.id} created. Waiting for seller response.", reply_markup=main_menu())
                return
    await message.answer("Welcome to Crypto Escrow Bot. Use the website to create a project, then continue here.", reply_markup=main_menu())

@router.message(Command('admin'))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer('Admin only.')
    async with AsyncSessionLocal() as session:
        projects = (await session.scalars(select(Project).order_by(Project.created_at.desc()).limit(10))).all()
    text = 'Admin Dashboard\n\n' + '\n'.join([f'#{p.id} - {p.status} - ${p.budget} - {p.project_type}' for p in projects])
    await message.answer(text or 'No projects yet.')

@router.callback_query(F.data.startswith('seller_terms:'))
async def seller_terms(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name, 'seller')
        user.terms_accepted = True
        await session.commit()
    await call.message.answer('Seller terms accepted. You can now accept offers.')
    await call.answer()

@router.callback_query(F.data.startswith('seller_accept:'))
async def seller_accept(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name, 'seller')
        if not user.terms_accepted:
            return await call.message.answer('Please accept seller terms first.')
        project = await session.get(Project, pid)
        project.seller_id = user.id
        project.status = 'Awaiting Payment'
        await add_message(session, pid, 'Seller accepted the project offer.', user.id)
        await session.commit()
        client = await session.get(User, project.client_id) if project.client_id else None
    await call.message.answer('Offer accepted. Waiting for client payment.')
    if client and client.telegram_id:
        await bot.send_message(client.telegram_id, f'Seller accepted project #{pid}. Please continue to payment.', reply_markup=payment_button(pid))
    await call.answer()

@router.callback_query(F.data.startswith('seller_decline:'))
async def seller_decline(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        project.status = 'Cancelled'
        await session.commit()
    await call.message.answer('Offer declined.')
    await call.answer()

@router.callback_query(F.data.startswith('client_terms:'))
async def client_terms(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name)
        user.escrow_terms_accepted = True
        await session.commit()
    await call.message.answer('Escrow terms accepted. You can now make payment.', reply_markup=coins(pid))
    await call.answer()

@router.callback_query(F.data.startswith('make_payment:'))
async def make_payment(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name)
        if not user.escrow_terms_accepted:
            return await call.message.answer('Please accept escrow terms first.')
    await call.message.answer('Select payment coin:', reply_markup=coins(pid))
    await call.answer()

@router.callback_query(F.data.startswith('coin:'))
async def coin_select(call: CallbackQuery, bot: Bot):
    _, pid, coin = call.data.split(':')
    pid = int(pid)
    wallets = {'USDT': settings.usdt_wallet_address, 'USDC': settings.usdc_wallet_address, 'BTC': settings.btc_wallet_address}
    wallet = wallets.get(coin) or 'WALLET_NOT_CONFIGURED'
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        payment = await create_payment(session, project, coin, wallet)
    qr_text = f'{coin}:{wallet}?amount={payment.amount_due}'
    img = qrcode.make(qr_text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    await call.message.answer_photo(BufferedInputFile(buf.read(), filename='payment_qr.png'), caption=f'Project #{pid}\nPay {payment.amount_due:.2f} USD worth of {coin}\nWallet:\n`{wallet}`\n\nAfter payment, send your transaction hash here.', parse_mode='Markdown')
    STATE[call.from_user.id] = ('tx_hash', pid)
    await notify_admins(bot, f'Payment started for project #{pid}. Waiting for TX hash.', pid)
    await call.answer()

@router.message(F.text)
async def text_state(message: Message, bot: Bot):
    state = STATE.get(message.from_user.id)
    if not state:
        return
    action, pid = state
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
        project = await session.get(Project, pid) if pid else None
        if action == 'tx_hash':
            payment = await session.scalar(select(Payment).where(Payment.project_id == pid).order_by(Payment.created_at.desc()))
            payment.tx_hash = message.text.strip()
            await add_message(session, pid, f'TX hash submitted: {message.text}', user.id)
            await session.commit()
            STATE.pop(message.from_user.id, None)
            await message.answer('TX hash received. Payment is pending confirmation.')
            await notify_admins(bot, f'Project #{pid} TX hash submitted:\n{message.text}\nConfirm after checking payment.', pid)
        elif action == 'submit_delivery':
            session.add(Delivery(project_id=pid, seller_id=user.id, message=message.text, file_id=None))
            project.status = 'Submitted'
            project.submitted_at = datetime.utcnow()
            await session.commit()
            STATE.pop(message.from_user.id, None)
            await message.answer('Project submitted. Waiting for client approval.')
            client = await session.get(User, project.client_id)
            if client and client.telegram_id:
                await bot.send_message(client.telegram_id, f'Seller submitted project #{pid}:\n{message.text}', reply_markup=client_review(pid))
        elif action == 'dispute_reason':
            session.add(Dispute(project_id=pid, opened_by_user_id=user.id, reason=message.text))
            project.status = 'Dispute'
            await session.commit()
            STATE.pop(message.from_user.id, None)
            await message.answer('Dispute opened. Admin will review.')
            await notify_admins(bot, f'Dispute opened for project #{pid}:\n{message.text}', pid)
        elif action == 'withdraw_amount':
            try:
                amount = float(message.text)
            except ValueError:
                return await message.answer('Enter valid amount.')
            STATE[message.from_user.id] = (f'withdraw_wallet:{amount}', None)
            await message.answer('Enter withdrawal wallet address.')
        elif action.startswith('withdraw_wallet:'):
            amount = float(action.split(':')[1])
            if amount > user.balance:
                STATE.pop(message.from_user.id, None)
                return await message.answer('Insufficient balance.')
            user.balance -= amount
            session.add(Withdrawal(user_id=user.id, amount=amount, wallet_address=message.text.strip()))
            await session.commit()
            STATE.pop(message.from_user.id, None)
            await message.answer('Withdrawal request submitted to admin.')
            await notify_admins(bot, f'Withdrawal request: @{user.telegram_username} ${amount}\nWallet: {message.text}')

@router.callback_query(F.data.startswith('admin_confirm:'))
async def admin_confirm(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id): return await call.answer('Admin only')
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        payment = await session.scalar(select(Payment).where(Payment.project_id == pid).order_by(Payment.created_at.desc()))
        project.payment_status = 'Confirmed'; project.status = 'In Progress'; project.deadline_at = datetime.utcnow() + timedelta(days=project.timeline_days)
        if payment: payment.status = 'Confirmed'
        await session.commit()
        seller = await session.get(User, project.seller_id)
        client = await session.get(User, project.client_id)
    for u, text in [(seller, 'Payment confirmed. Start working.'), (client, 'Payment confirmed. Project is now in progress.')]:
        if u and u.telegram_id: await bot.send_message(u.telegram_id, f'Project #{pid}: {text}', reply_markup=seller_project(pid) if u == seller else None)
    await call.message.answer('Payment confirmed.')

@router.callback_query(F.data.startswith('submit:'))
async def submit_project(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    STATE[call.from_user.id] = ('submit_delivery', pid)
    await call.message.answer('Send the project delivery message/link/files description now.')

@router.callback_query(F.data.startswith('approve:'))
async def approve(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        await release_seller_funds(session, project)
        seller = await session.get(User, project.seller_id)
    await call.message.answer('Project approved. Funds released to seller balance. Please rate the seller from 1-5.')
    if seller and seller.telegram_id: await bot.send_message(seller.telegram_id, f'Project #{pid} approved. Your balance has been updated.')

@router.callback_query(F.data.startswith('revision:'))
async def revision(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        if project.revision_count >= project.revision_limit:
            project.status = 'Dispute'
            await session.commit()
            await notify_admins(bot, f'Project #{pid} reached revision limit. Admin review needed.', pid)
            return await call.message.answer('Revision limit reached. Project moved to admin review.')
        project.revision_count += 1; project.status = 'Revision'
        await session.commit()
        seller = await session.get(User, project.seller_id)
    await call.message.answer('Revision requested.')
    if seller and seller.telegram_id: await bot.send_message(seller.telegram_id, f'Revision requested for project #{pid}.', reply_markup=seller_project(pid))

@router.callback_query(F.data.startswith('dispute:'))
async def dispute(call: CallbackQuery):
    pid = int(call.data.split(':')[1])
    STATE[call.from_user.id] = ('dispute_reason', pid)
    await call.message.answer('Describe the issue for admin dispute review.')

@router.callback_query(F.data.startswith('cancel:'))
async def cancel(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, pid)
        project.status = 'Cancellation Requested'
        await session.commit()
        seller = await session.get(User, project.seller_id)
    await call.message.answer('Cancellation requested. Seller/admin will review.')
    if seller and seller.telegram_id: await bot.send_message(seller.telegram_id, f'Client requested cancellation for project #{pid}. Admin handles final split if needed.')
    await notify_admins(bot, f'Cancellation requested for project #{pid}.', pid)

@router.callback_query(F.data.startswith('admin_pause:'))
async def admin_pause(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer('Admin only')
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        p = await session.get(Project, pid); p.paused = True; p.status = 'Paused'; await session.commit()
    await call.message.answer('Project paused.')

@router.callback_query(F.data.startswith('admin_extend:'))
async def admin_extend(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer('Admin only')
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        p = await session.get(Project, pid); p.deadline_at = (p.deadline_at or datetime.utcnow()) + timedelta(days=2); p.paused = False; p.status = 'In Progress'; await session.commit()
    await call.message.answer('Deadline extended by 2 days.')

@router.callback_query(F.data.startswith('admin_release:'))
async def admin_release(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer('Admin only')
    pid = int(call.data.split(':')[1])
    async with AsyncSessionLocal() as session:
        p = await session.get(Project, pid); await release_seller_funds(session, p)
    await call.message.answer('Seller funds released.')

@router.callback_query(F.data == 'menu:balance')
async def balance(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.full_name)
    await call.message.answer(f'Balance: ${user.balance:.2f}\nSend /withdraw to request withdrawal.')

@router.message(Command('withdraw'))
async def withdraw(message: Message):
    STATE[message.from_user.id] = ('withdraw_amount', None)
    await message.answer('Enter withdrawal amount.')
