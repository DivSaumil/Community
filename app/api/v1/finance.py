import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.crud import finance as crud_finance
from app.models.users import User, Flat
from app.models.finance import Invoice
from app.schemas.finance import (
    InvoiceOut,
    InvoiceCreate,
    PaymentOut,
    PaymentCreate,
    ExpenseOut,
    ExpenseCreate,
    BudgetOut,
    BudgetCreate,
    FinancialSummary,
)

router = APIRouter()

# Role checkers
admin_required = RoleChecker(["admin"])
admin_or_staff_required = RoleChecker(["admin", "staff"])

def check_finance_access(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "resident", "tenant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Guards and staff cannot access financial information."
        )
    return current_user


@router.post("/invoices", response_model=InvoiceOut, dependencies=[Depends(admin_required)])
async def create_maintenance_invoice(payload: InvoiceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate maintenance billing invoice for a flat. Admin only."""
    return await crud_finance.create_invoice(db, payload, current_user.id)


@router.get("/invoices", response_model=List[InvoiceOut], dependencies=[Depends(admin_required)])
async def list_all_invoices(
    flat_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    """List all society invoices. Admin only."""
    return await crud_finance.get_all_invoices(db, flat_id, status)


@router.get("/my-invoices", response_model=List[InvoiceOut])
async def list_my_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_finance_access)
):
    """Retrieve invoices linked to flats occupied by the current resident/tenant."""
    # Find all flats where user is owner or tenant
    flat_query = select(Flat.id).where(
        (Flat.owner_id == current_user.id) | (Flat.tenant_id == current_user.id)
    )
    flat_res = await db.execute(flat_query)
    flat_ids = list(flat_res.scalars().all())
    
    if not flat_ids:
        return []
        
    invoice_query = select(Invoice).where(Invoice.flat_id.in_(flat_ids)).order_by(Invoice.due_date.desc())
    invoice_res = await db.execute(invoice_query)
    return list(invoice_res.scalars().all())


@router.post("/pay", response_model=PaymentOut)
async def pay_invoice(payload: PaymentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(check_finance_access)):
    """Process a mock invoice payment. Residents can pay their dues."""
    payment = await crud_finance.create_payment(db, payload, current_user.id)
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return payment


@router.post("/expenses", response_model=ExpenseOut, dependencies=[Depends(admin_required)])
async def record_expense(payload: ExpenseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Record a society operation expense. Admin only."""
    return await crud_finance.create_expense(db, payload, current_user.id)


@router.get("/expenses", response_model=List[ExpenseOut])
async def list_expenses(category: str | None = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(check_finance_access)):
    """List recorded society expenses. Accessible by admin, resident, and tenant."""
    return await crud_finance.get_expenses(db, category)


@router.post("/budgets", response_model=BudgetOut, dependencies=[Depends(admin_required)])
async def create_budget_allocation(payload: BudgetCreate, db: AsyncSession = Depends(get_db)):
    """Set budget allocation for a category. Admin only."""
    return await crud_finance.create_budget(db, payload)


@router.get("/budgets", response_model=List[BudgetOut])
async def list_budgets(db: AsyncSession = Depends(get_db), current_user: User = Depends(check_finance_access)):
    """List overall budgets allocations. Accessible by admin, resident, and tenant."""
    return await crud_finance.get_budgets(db)


@router.get("/summary", response_model=FinancialSummary)
async def get_financial_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(check_finance_access)):
    """Get overall society financial transparency summary figures. Accessible by admin, resident, and tenant."""
    return await crud_finance.get_financial_summary(db)
