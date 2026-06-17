import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.crud import users as crud_users
from app.models.users import User, Flat, FamilyMember
from app.schemas.users import UserOut, UserCreate, FlatOut, FlatCreate, UserUpdate, FamilyMemberCreate, FamilyMemberOut

router = APIRouter()

# Admin checks
admin_required = RoleChecker(["admin"])


def enrich_user_schema(user: User) -> UserOut:
    """Helper to construct enriched UserOut schema from a User object that already has loaded flat relations."""
    flats_list = []
    flats_detailed = []
    for f in user.owned_flats:
        flats_list.append(f"{f.block}-{f.flat_number}")
        flats_detailed.append(f)
    for f in user.rented_flats:
        flats_list.append(f"{f.block}-{f.flat_number}")
        flats_detailed.append(f)
        
    user_out = UserOut.model_validate(user)
    user_out.flats = sorted(list(set(flats_list)))
    
    seen_ids = set()
    unique_flats = []
    for f in flats_detailed:
        if f.id not in seen_ids:
            seen_ids.add(f.id)
            unique_flats.append(f)
    user_out.flats_detailed = unique_flats
    user_out.family_members = getattr(user, "family_members", []) or []
    return user_out


async def enrich_user_out(db: AsyncSession, db_user: User) -> UserOut:
    """Helper to load flat relations and construct enriched UserOut schema."""
    result = await db.execute(
        select(User)
        .where(User.id == db_user.id)
        .options(
            selectinload(User.owned_flats),
            selectinload(User.rented_flats),
            selectinload(User.family_members),
        )
    )
    user = result.scalar_one()
    return enrich_user_schema(user)


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
    result = await db.execute(
        select(User)
        .where(User.role == "staff")
        .options(
            selectinload(User.owned_flats),
            selectinload(User.rented_flats),
            selectinload(User.family_members),
        )
    )
    users = result.scalars().all()
    return [enrich_user_schema(u) for u in users]


@router.get("", response_model=List[UserOut], dependencies=[Depends(admin_required)])
async def list_all_users(
    role: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in the system (Admin only).
    """
    stmt = select(User).options(
        selectinload(User.owned_flats),
        selectinload(User.rented_flats),
        selectinload(User.family_members),
    )
    if role:
        stmt = stmt.where(User.role == role)
    if search:
        search_filter = f"%{search.strip().lower()}%"
        from sqlalchemy import or_
        stmt = stmt.where(or_(User.name.ilike(search_filter), User.email.ilike(search_filter)))
    
    stmt = stmt.order_by(User.name).offset(offset).limit(limit)
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [enrich_user_schema(u) for u in users]


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(admin_required)])
async def update_user_by_admin(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update details of any user (Admin only).
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated = await crud_users.update_user(db, user, payload)
    return await enrich_user_out(db, updated)


# ─────────────────────────────────────────────
# Family Member Router
# ─────────────────────────────────────────────

@router.get("/me/family", response_model=List[FamilyMemberOut])
async def list_my_family(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List family members for the current logged-in user."""
    stmt = select(FamilyMember).where(FamilyMember.user_id == current_user.id).order_by(FamilyMember.created_at)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/me/family", response_model=FamilyMemberOut, status_code=status.HTTP_201_CREATED)
async def add_family_member(
    payload: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a family member to the current user's profile."""
    db_member = FamilyMember(
        user_id=current_user.id,
        name=payload.name,
        relation=payload.relation,
        phone=payload.phone,
        email=payload.email,
    )
    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)
    return db_member


@router.put("/me/family/{member_id}", response_model=FamilyMemberOut)
async def update_family_member(
    member_id: uuid.UUID,
    payload: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update details of a family member."""
    stmt = select(FamilyMember).where(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
    res = await db.execute(stmt)
    db_member = res.scalar_one_or_none()
    if not db_member:
        raise HTTPException(status_code=404, detail="Family member not found")
        
    db_member.name = payload.name
    db_member.relation = payload.relation
    db_member.phone = payload.phone
    db_member.email = payload.email
    await db.commit()
    await db.refresh(db_member)
    return db_member


@router.delete("/me/family/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a family member."""
    stmt = select(FamilyMember).where(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
    res = await db.execute(stmt)
    db_member = res.scalar_one_or_none()
    if not db_member:
        raise HTTPException(status_code=404, detail="Family member not found")
        
    await db.delete(db_member)
    await db.commit()
    return

