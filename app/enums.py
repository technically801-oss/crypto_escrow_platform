from enum import Enum

class UserRole(str, Enum):
    CLIENT = 'client'
    SELLER = 'seller'
    ADMIN = 'admin'

class ProjectStatus(str, Enum):
    PENDING_DISCUSSION = 'Pending Discussion'
    AWAITING_PAYMENT = 'Awaiting Payment'
    PAID = 'Paid'
    ACCEPTED = 'Accepted'
    IN_PROGRESS = 'In Progress'
    SUBMITTED = 'Submitted'
    REVISION = 'Revision'
    DISPUTE = 'Dispute'
    APPROVED = 'Approved'
    CANCEL_REQUESTED = 'Cancellation Requested'
    CANCELLED = 'Cancelled'
    COMPLETED = 'Completed'
    EXPIRED = 'Expired'
    ADMIN_REVIEW = 'Admin Review'
    PAUSED = 'Paused'

class PaymentStatus(str, Enum):
    PENDING = 'Pending'
    CONFIRMED = 'Confirmed'
    FAILED = 'Failed'
    REFUNDED = 'Refunded'
    RELEASED = 'Released'

class CryptoCoin(str, Enum):
    USDT = 'USDT'
    USDC = 'USDC'
    BTC = 'BTC'
