from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb(rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
            for row in rows
        ]
    )


def client_menu():
    return kb([
        [('My Projects', 'menu:client_projects'), ('Balance', 'menu:balance')],
        [('Pending Payments', 'menu:pending_payments')],
        [('Support', 'menu:support')],
    ])


def seller_menu():
    return kb([
        [('New Offers', 'menu:seller_offers'), ('My Jobs', 'menu:seller_projects')],
        [('Balance', 'menu:balance'), ('Withdraw', 'menu:withdraw')],
        [('Support', 'menu:support')],
    ])


def admin_menu():
    return kb([
        [('All Projects', 'menu:admin_projects'), ('Disputes', 'menu:admin_disputes')],
        [('Withdrawals', 'menu:admin_withdrawals')],
    ])


def start_role_menu():
    return kb([
        [('Continue as Client', 'role:client')],
        [('Continue as Seller', 'role:seller')],
    ])


def seller_offer(project_id: int):
    return kb([
        [('Accept Terms', f'seller_terms:{project_id}')],
        [('Accept Offer', f'seller_accept:{project_id}'), ('Decline', f'seller_decline:{project_id}')],
    ])


def payment_button(project_id: int):
    return kb([
        [('Accept Escrow Terms', f'client_terms:{project_id}')],
        [('Make Payment', f'make_payment:{project_id}')],
    ])


def coins(project_id: int):
    return kb([
        [('USDT', f'coin:{project_id}:USDT'), ('USDC', f'coin:{project_id}:USDC'), ('BTC', f'coin:{project_id}:BTC')],
    ])


def client_review(project_id: int):
    return kb([
        [('Approve', f'approve:{project_id}'), ('Request Revision', f'revision:{project_id}')],
        [('Decline / Dispute', f'dispute:{project_id}'), ('Cancel', f'cancel:{project_id}')],
    ])


def seller_project(project_id: int):
    return kb([
        [('Submit Project', f'submit:{project_id}'), ('Request More Time', f'extend:{project_id}')],
    ])


def admin_project(project_id: int):
    return kb([
        [('Confirm Payment', f'admin_confirm:{project_id}'), ('Reject Payment', f'admin_reject:{project_id}')],
        [('Pause', f'admin_pause:{project_id}'), ('Extend Deadline', f'admin_extend:{project_id}')],
        [('Release Seller', f'admin_release:{project_id}'), ('Refund Client', f'admin_refund:{project_id}')],
    ])