from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Telegram IDs can be bigger than normal Integer, so use BigInteger
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
    )

    telegram_username: Mapped[str | None] = mapped_column(String(100), index=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200), index=True)

    role: Mapped[str] = mapped_column(String(20), default="client")
    password: Mapped[str | None] = mapped_column(String(200))

    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    escrow_terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)

    balance: Mapped[float] = mapped_column(Float, default=0.0)

    referral_code: Mapped[str | None] = mapped_column(String(100), index=True)
    referred_by_seller_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    seller_telegram_username: Mapped[str | None] = mapped_column(String(100), index=True)

    project_type: Mapped[str] = mapped_column(String(120))
    budget: Mapped[float] = mapped_column(Float)
    timeline_days: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(50), default="Pending Discussion")
    payment_status: Mapped[str] = mapped_column(String(50), default="Pending")

    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    revision_limit: Mapped[int] = mapped_column(Integer, default=2)

    paused: Mapped[bool] = mapped_column(Boolean, default=False)

    referral_seller_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    coin: Mapped[str] = mapped_column(String(20))
    amount_due: Mapped[float] = mapped_column(Float)
    wallet_address: Mapped[str] = mapped_column(String(255))

    tx_hash: Mapped[str | None] = mapped_column(String(255))
    proof_file_id: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(50), default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    message: Mapped[str] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    opened_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="Open")
    admin_decision: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)
    wallet_address: Mapped[str] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(50), default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    amount: Mapped[float] = mapped_column(Float)
    wallet_address: Mapped[str] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(50), default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectMessage(Base):
    __tablename__ = "project_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    message: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    stars: Mapped[int] = mapped_column(Integer)
    review: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)