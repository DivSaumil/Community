import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.crud import complaints as crud_complaints
from app.models.users import User, Flat
from app.models.complaints import Complaint
from app.schemas.complaints import (
    ComplaintOut,
    ComplaintCreate,
    ComplaintUpdate,
    CommentOut,
    CommentCreate,
)

router = APIRouter()

# Role checks
admin_or_staff_required = RoleChecker(["admin", "staff"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
async def raise_complaint(payload: ComplaintCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Raise a new ticket/complaint. Residents and tenants can use this."""
    # Verify flat belongs to user
    flat_query = select(Flat).where(Flat.id == payload.flat_id)
    flat_res = await db.execute(flat_query)
    flat = flat_res.scalar_one_or_none()
    
    if not flat:
        raise HTTPException(status_code=404, detail="Flat not found")
        
    if current_user.role not in ["admin"] and flat.owner_id != current_user.id and flat.tenant_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to raise a complaint for this flat",
        )
        
    return await crud_complaints.create_complaint(db, payload, current_user.id)


@router.get("", response_model=List[ComplaintOut])
async def list_complaints(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List complaints.
    Admins and staff can see all.
    Residents/tenants can only see their own flat's complaints.
    """
    if current_user.role in ["admin", "staff"]:
        return await crud_complaints.get_all_complaints(
            db, status=status, category=category, priority=priority, limit=limit, offset=offset
        )
    else:
        # Find user's flats
        flat_query = select(Flat.id).where(
            (Flat.owner_id == current_user.id) | (Flat.tenant_id == current_user.id)
        )
        flat_res = await db.execute(flat_query)
        flat_ids = list(flat_res.scalars().all())
        
        # Query
        query = select(Complaint).options(selectinload(Complaint.comments))
        if flat_ids:
            query = query.where(
                (Complaint.raised_by_id == current_user.id) | (Complaint.flat_id.in_(flat_ids))
            )
        else:
            query = query.where(Complaint.raised_by_id == current_user.id)
            
        if status:
            query = query.where(Complaint.status == status)
        if category:
            query = query.where(Complaint.category == category)
        if priority:
            query = query.where(Complaint.priority == priority)
            
        query = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())


@router.get("/{complaint_id}", response_model=ComplaintOut)
async def get_complaint_details(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full details of a specific complaint, including its conversation log."""
    complaint = await crud_complaints.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Check permissions: only admin/staff or the flat owner/tenant can access
    if current_user.role not in ["admin", "staff"]:
        flat_query = select(Flat).where(Flat.id == complaint.flat_id)
        flat_res = await db.execute(flat_query)
        flat = flat_res.scalar_one_or_none()
        if not flat or (flat.owner_id != current_user.id and flat.tenant_id != current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
            
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintOut)
async def update_complaint_status(
    complaint_id: uuid.UUID,
    payload: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update complaint details.
    Admins/Staff can reassign, change priority or update status (e.g. Open -> In Progress -> Resolved).
    Residents can only transition status to 'closed' when a ticket is resolved.
    """
    complaint = await crud_complaints.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    if current_user.role not in ["admin", "staff"]:
        # Resident check
        flat_query = select(Flat).where(Flat.id == complaint.flat_id)
        flat_res = await db.execute(flat_query)
        flat = flat_res.scalar_one_or_none()
        if not flat or (flat.owner_id != current_user.id and flat.tenant_id != current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
            
        # Residents can only close a complaint
        if payload.status != "closed":
            raise HTTPException(
                status_code=403,
                detail="Residents can only change status to 'closed' when resolving",
            )
        # Prevent residents from changing assignment or priority
        if payload.assigned_to_id or payload.priority:
            raise HTTPException(
                status_code=403,
                detail="Residents cannot change ticket assignment or priority",
            )
            
    return await crud_complaints.update_complaint(db, complaint, payload)


@router.post("/{complaint_id}/comments", response_model=CommentOut)
async def add_complaint_comment(
    complaint_id: uuid.UUID,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post a chat message/update comment on a complaint ticket."""
    complaint = await crud_complaints.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Check permissions
    if current_user.role not in ["admin", "staff"]:
        flat_query = select(Flat).where(Flat.id == complaint.flat_id)
        flat_res = await db.execute(flat_query)
        flat = flat_res.scalar_one_or_none()
        if not flat or (flat.owner_id != current_user.id and flat.tenant_id != current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
            
    return await crud_complaints.create_complaint_comment(db, payload, current_user.id, complaint_id)
