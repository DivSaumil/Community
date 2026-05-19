import uuid
import random
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
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
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()


async def get_all_invoices(
    db: AsyncSession, flat_id: uuid.UUID | None = None, status: str | None = None
) -> list[Invoice]:
    query = select(Invoice)
    if flat_id:
        query = query.where(Invoice.flat_id == flat_id)
    if status:
        query = query.where(Invoice.status == status)
    query = query.order_by(Invoice.due_date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_payment(db: AsyncSession, payment_in: PaymentCreate, user_id: uuid.UUID) -> Payment | None:
    # 1. Fetch the invoice
    invoice = await get_invoice(db, payment_in.invoice_id)
    if not invoice:
        return None
        
    # Generate receipt number
    receipt_num = f"REC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
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
    # Simple logic: if payment amount matches or exceeds invoice amount (plus late fee), mark paid.
    # Otherwise partially_paid.
    total_due = invoice.amount + invoice.late_fee
    if payment_in.amount >= total_due:
        invoice.status = "paid"
    else:
        invoice.status = "partially_paid"
        
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return db_payment


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


async def get_expenses(db: AsyncSession, category: str | None = None) -> list[Expense]:
    query = select(Expense)
    if category:
        query = query.where(Expense.category == category)
    query = query.order_by(Expense.spent_date.desc())
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


async def get_budgets(db: AsyncSession) -> list[Budget]:
    result = await db.execute(select(Budget).order_by(Budget.start_date.desc()))
    return list(result.scalars().all())


async def get_financial_summary(db: AsyncSession) -> dict:
    # 1. Total billed
    res_billed = await db.execute(select(func.sum(Invoice.amount)))
    total_billed = res_billed.scalar() or Decimal("0.00")
    
    # 2. Total collected
    res_collected = await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == "completed")
    )
    total_collected = res_collected.scalar() or Decimal("0.00")
    
    # 3. Total pending (amount + late_fee where status is unpaid/partially_paid/overdue)
    res_pending = await db.execute(
        select(func.sum(Invoice.amount + Invoice.late_fee)).where(Invoice.status != "paid")
    )
    total_pending = res_pending.scalar() or Decimal("0.00")
    
    # 4. Total expenses
    res_expenses = await db.execute(select(func.sum(Expense.amount)))
    total_expenses = res_expenses.scalar() or Decimal("0.00")
    
    # 5. Pending invoices count
    res_count = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.status != "paid")
    )
    pending_count = res_count.scalar() or 0
    
    return {
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_pending": total_pending,
        "total_expenses": total_expenses,
        "pending_invoices_count": pending_count,
    }
