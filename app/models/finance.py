import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g., "Maintenance Fee - May 2026"
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unpaid", nullable=False)  # unpaid, paid, partially_paid, overdue
    late_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)  # UPI, CARD, NET_BANKING, CASH
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, completed, failed
    paid_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")
    paid_by: Mapped["User"] = relationship("User", back_populates="payments")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # Housekeeping, Security, Maintenance, Utility, Events, Other
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    spent_date: Mapped[date] = mapped_column(Date, nullable=False)
    spent_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
