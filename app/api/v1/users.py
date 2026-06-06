import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.crud import users as crud_users
from app.models.users import User
from app.schemas.users import UserOut, UserCreate, FlatOut, FlatCreate, UserUpdate

router = APIRouter()

# Admin checks
admin_required = RoleChecker(["admin"])


async def enrich_user_out(db: AsyncSession, db_user: User) -> UserOut:
    """Helper to load flat relations and construct enriched UserOut schema."""
    result = await db.execute(
        select(User)
        .where(User.id == db_user.id)
        .options(selectinload(User.owned_flats), selectinload(User.rented_flats))
    )
    user = result.scalar_one()
    
    flats_list = []
    for f in user.owned_flats:
        flats_list.append(f"{f.block}-{f.flat_number}")
    for f in user.rented_flats:
        flats_list.append(f"{f.block}-{f.flat_number}")
        
    user_out = UserOut.model_validate(user)
    user_out.flats = sorted(list(set(flats_list)))
    return user_out


@router.get("/me", response_model=UserOut)
async def read_user_me(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve the current logged-in user's profile."""
    return await enrich_user_out(db, current_user)


@router.put("/me", response_model=UserOut)
async def update_user_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's profile details (e.g. name, vehicle_number)."""
    # Prevent non-admin users from updating their role or active status
    if current_user.role != "admin":
        payload.role = None
        payload.is_active = None
        
    updated = await crud_users.update_user(db, current_user, payload)
    return await enrich_user_out(db, updated)


@router.post("/register", response_model=UserOut, dependencies=[Depends(admin_required)])
async def register_user_manually(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Onboard/Register a new user manually.
    Only accessible by Admin.
    """
    existing_user = await crud_users.get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered",
        )
    user = await crud_users.create_user(db, payload)
    return await enrich_user_out(db, user)


@router.get("/flats", response_model=List[FlatOut])
async def list_flats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get list of all flats in the society."""
    return await crud_users.get_all_flats(db)


@router.post("/flats", response_model=FlatOut, dependencies=[Depends(admin_required)])
async def create_new_flat(payload: FlatCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new flat layout.
    Only accessible by Admin.
    """
    existing_flat = await crud_users.get_flat_by_details(db, payload.block, payload.flat_number)
    if existing_flat:
        raise HTTPException(
            status_code=400,
            detail=f"Flat {payload.block}-{payload.flat_number} already exists",
        )
    return await crud_users.create_flat(db, payload)


@router.post("/flats/{flat_id}/assign", response_model=FlatOut, dependencies=[Depends(admin_required)])
async def assign_occupants(
    flat_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Assign owner and/or tenant to a flat.
    Only accessible by Admin.
    """
    flat = await crud_users.assign_user_to_flat(db, flat_id, owner_id, tenant_id)
    if not flat:
        raise HTTPException(status_code=404, detail="Flat not found")
    return flat


@router.get("/by-email/{email}", response_model=UserOut)
async def get_user_by_email_address(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of any registered user by their email address."""
    user = await crud_users.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await enrich_user_out(db, user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of any registered user by their ID."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await enrich_user_out(db, user)


@router.get("/staff", response_model=List[UserOut])
async def list_society_staff(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all staff/vendor accounts (e.g. electricians, plumbers)."""
    result = await db.execute(select(User).where(User.role == "staff"))
    users = result.scalars().all()
    enriched = []
    for u in users:
        enriched.append(await enrich_user_out(db, u))
    return enriched
