import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import User, Flat
from app.schemas.users import UserCreate, FlatCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role,
        vehicle_number=user_in.vehicle_number,
    )
    db.add(db_user)
    await db.flush()

    if user_in.block and user_in.flat_number:
        flat = await get_flat_by_details(db, user_in.block, user_in.flat_number)
        if not flat:
            flat = Flat(block=user_in.block, flat_number=user_in.flat_number)
            db.add(flat)
            await db.flush()
        
        if user_in.role == "resident" or user_in.role == "admin":
            flat.owner_id = db_user.id
        elif user_in.role == "tenant":
            flat.tenant_id = db_user.id

    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    if user_in.name is not None:
        db_user.name = user_in.name
    if user_in.role is not None:
        db_user.role = user_in.role
    if user_in.is_active is not None:
        db_user.is_active = user_in.is_active
    if hasattr(user_in, "vehicle_number") and user_in.vehicle_number is not None:
        db_user.vehicle_number = user_in.vehicle_number

    # Handle flat update
    if user_in.block is not None and user_in.flat_number is not None:
        # 1. Unassign from old flats
        from sqlalchemy import or_
        old_flats_res = await db.execute(
            select(Flat).where(or_(Flat.owner_id == db_user.id, Flat.tenant_id == db_user.id))
        )
        old_flats = old_flats_res.scalars().all()
        for f in old_flats:
            if f.owner_id == db_user.id:
                f.owner_id = None
            if f.tenant_id == db_user.id:
                f.tenant_id = None
        
        # 2. Assign to new flat
        block = user_in.block.strip()
        flat_number = user_in.flat_number.strip()
        if block and flat_number:
            flat = await get_flat_by_details(db, block, flat_number)
            if not flat:
                flat = Flat(block=block, flat_number=flat_number)
                db.add(flat)
                await db.flush()
            
            role = user_in.role or db_user.role
            if role == "resident" or role == "admin":
                flat.owner_id = db_user.id
            elif role == "tenant":
                flat.tenant_id = db_user.id

    await db.commit()
    await db.refresh(db_user)
    return db_user



async def get_flat(db: AsyncSession, flat_id: uuid.UUID) -> Flat | None:
    result = await db.execute(select(Flat).where(Flat.id == flat_id))
    return result.scalar_one_or_none()


async def get_flat_by_details(db: AsyncSession, block: str, flat_number: str) -> Flat | None:
    result = await db.execute(
        select(Flat).where(Flat.block == block, Flat.flat_number == flat_number)
    )
    return result.scalar_one_or_none()


async def create_flat(db: AsyncSession, flat_in: FlatCreate) -> Flat:
    db_flat = Flat(
        block=flat_in.block,
        flat_number=flat_in.flat_number,
        owner_id=flat_in.owner_id,
        tenant_id=flat_in.tenant_id,
    )
    db.add(db_flat)
    await db.commit()
    await db.refresh(db_flat)
    return db_flat


async def get_all_flats(db: AsyncSession) -> list[Flat]:
    result = await db.execute(select(Flat).order_by(Flat.block, Flat.flat_number))
    return list(result.scalars().all())


async def assign_user_to_flat(
    db: AsyncSession, flat_id: uuid.UUID, owner_id: uuid.UUID | None, tenant_id: uuid.UUID | None
) -> Flat | None:
    flat = await get_flat(db, flat_id)
    if not flat:
        return None
    if owner_id is not None:
        flat.owner_id = owner_id
    if tenant_id is not None:
        flat.tenant_id = tenant_id
    await db.commit()
    await db.refresh(flat)
    return flat
