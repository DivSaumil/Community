import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class InvoiceCreate(BaseModel):
    flat_id: uuid.UUID | str
    title: str = Field(..., max_length=200, examples=["Maintenance Fee - May 2026"])
    amount: Decimal = Field(..., gt=0)
    due_date: date


class InvoiceOut(BaseModel):
    id: uuid.UUID
    flat_id: uuid.UUID
    title: str
    amount: Decimal
    due_date: date
    status: str
    late_fee: Decimal
    created_by_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field("UPI", description="UPI, CARD, NET_BANKING, CASH")
    transaction_id: str | None = None


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    payment_method: str
    transaction_id: str | None
    status: str
    paid_by_id: uuid.UUID
    paid_at: datetime | None
    receipt_number: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    title: str = Field(..., max_length=200)
    category: str = Field("Other", description="Housekeeping, Security, Maintenance, Utility, Events, Other")
    amount: Decimal = Field(..., gt=0)
    spent_date: date
    receipt_url: str | None = None
    description: str | None = None


class ExpenseOut(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    amount: Decimal
    spent_date: date
    spent_by_id: uuid.UUID
    receipt_url: str | None
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    category: str
    allocated_amount: Decimal = Field(..., gt=0)
    start_date: date
    end_date: date


class BudgetOut(BaseModel):
    id: uuid.UUID
    category: str
    allocated_amount: Decimal
    start_date: date
    end_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialSummary(BaseModel):
    total_billed: Decimal
    total_collected: Decimal
    total_pending: Decimal
    total_expenses: Decimal
    pending_invoices_count: int
