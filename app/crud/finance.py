import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import Invoice, Payment, Expense, Budget
from app.schemas.finance import InvoiceCreate, PaymentCreate, ExpenseCreate, BudgetCreate


async def create_invoice(db: AsyncSession, invoice_in: InvoiceCreate, admin_id: uuid.UUID) -> Invoice:
    db_invoice = Invoice(
        flat_id=invoice_in.flat_id,
        title=invoice_in.title,
        amount=invoice_in.amount,
        due_date=invoice_in.due_date,
        status="unpaid",
        created_by_id=admin_id,
    )
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Invoice | None:
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def get_all_invoices(
    db: AsyncSession, 
    flat_id: uuid.UUID | None = None, 
    status: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[Invoice]:
    query = select(Invoice).where(Invoice.is_deleted == False)
    if flat_id:
        query = query.where(Invoice.flat_id == flat_id)
    if status:
        query = query.where(Invoice.status == status)
    query = query.order_by(Invoice.due_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_payment(db: AsyncSession, payment_in: PaymentCreate, user_id: uuid.UUID) -> Payment | None:
    # 1. Fetch the invoice
    invoice = await get_invoice(db, payment_in.invoice_id)
    if not invoice:
        return None
        
    # Ensure receipt number sequence exists and get next value
    await db.execute(text("CREATE SEQUENCE IF NOT EXISTS receipt_number_seq START WITH 1000"))
    seq_res = await db.execute(text("SELECT nextval('receipt_number_seq')"))
    seq_val = seq_res.scalar()
    
    receipt_num = f"REC-{datetime.now().strftime('%Y%m%d')}-{seq_val}"
    
    db_payment = Payment(
        invoice_id=payment_in.invoice_id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        transaction_id=payment_in.transaction_id,
        status="completed",  # For simulation, auto-complete
        paid_by_id=user_id,
        paid_at=datetime.now(timezone.utc),
        receipt_number=receipt_num,
    )
    
    # Update invoice status
    total_due = invoice.amount + invoice.late_fee
    if payment_in.amount >= total_due:
        invoice.status = "paid"
    else:
        invoice.status = "partially_paid"
        
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return db_payment


async def get_payment(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def soft_delete_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> bool:
    invoice = await get_invoice(db, invoice_id)
    if not invoice:
        return False
    invoice.is_deleted = True
    invoice.deleted_at = datetime.now(timezone.utc)
    # Also soft-delete all payments associated with this invoice
    await db.execute(
        text("UPDATE payments SET is_deleted = :is_del, deleted_at = :del_at WHERE invoice_id = :inv_id")
        .bindparams(is_del=True, del_at=datetime.now(timezone.utc), inv_id=invoice_id)
    )
    await db.commit()
    return True


async def soft_delete_payment(db: AsyncSession, payment_id: uuid.UUID) -> bool:
    payment = await get_payment(db, payment_id)
    if not payment:
        return False
    payment.is_deleted = True
    payment.deleted_at = datetime.now(timezone.utc)
    # If a payment is deleted, revert invoice status back to unpaid (or recalculate)
    invoice = await db.get(Invoice, payment.invoice_id)
    if invoice:
        invoice.status = "unpaid"
    await db.commit()
    return True


async def create_expense(db: AsyncSession, expense_in: ExpenseCreate, user_id: uuid.UUID) -> Expense:
    db_expense = Expense(
        title=expense_in.title,
        category=expense_in.category,
        amount=expense_in.amount,
        spent_date=expense_in.spent_date,
        spent_by_id=user_id,
        receipt_url=expense_in.receipt_url,
        description=expense_in.description,
    )
    db.add(db_expense)
    await db.commit()
    await db.refresh(db_expense)
    return db_expense


async def get_expenses(
    db: AsyncSession, 
    category: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[Expense]:
    query = select(Expense)
    if category:
        query = query.where(Expense.category == category)
    query = query.order_by(Expense.spent_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_budget(db: AsyncSession, budget_in: BudgetCreate) -> Budget:
    db_budget = Budget(
        category=budget_in.category,
        allocated_amount=budget_in.allocated_amount,
        start_date=budget_in.start_date,
        end_date=budget_in.end_date,
    )
    db.add(db_budget)
    await db.commit()
    await db.refresh(db_budget)
    return db_budget


async def get_budgets(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[Budget]:
    result = await db.execute(
        select(Budget).order_by(Budget.start_date.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def get_financial_summary(db: AsyncSession) -> dict:
    # Single query database aggregation using subqueries
    stmt = select(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(Invoice.is_deleted == False).scalar_subquery().label("total_billed"),
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "completed", Payment.is_deleted == False).scalar_subquery().label("total_collected"),
        select(func.coalesce(func.sum(Invoice.amount + Invoice.late_fee), 0)).where(Invoice.status != "paid", Invoice.is_deleted == False).scalar_subquery().label("total_pending"),
        select(func.coalesce(func.sum(Expense.amount), 0)).scalar_subquery().label("total_expenses"),
        select(func.count(Invoice.id)).where(Invoice.status != "paid", Invoice.is_deleted == False).scalar_subquery().label("pending_invoices_count")
    )
    res = await db.execute(stmt)
    row = res.fetchone()
    
    if not row:
        return {
            "total_billed": Decimal("0.00"),
            "total_collected": Decimal("0.00"),
            "total_pending": Decimal("0.00"),
            "total_expenses": Decimal("0.00"),
            "pending_invoices_count": 0,
        }
        
    return {
        "total_billed": row.total_billed,
        "total_collected": row.total_collected,
        "total_pending": row.total_pending,
        "total_expenses": row.total_expenses,
        "pending_invoices_count": row.pending_invoices_count,
    }
