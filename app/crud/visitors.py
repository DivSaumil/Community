import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.visitors import VisitorPass, VisitorLog, DailyHelp, DailyHelpFlat
from app.schemas.visitors import VisitorPassCreate, VisitorLogCreate, DailyHelpCreate


async def create_visitor_pass(
    db: AsyncSession, pass_in: VisitorPassCreate, resident_id: uuid.UUID
) -> VisitorPass:
    valid_until = pass_in.valid_until or (pass_in.expected_arrival + timedelta(hours=24))
    
    for attempt in range(10):
        # Generate 6-digit unique pass code
        pass_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        
        db_pass = VisitorPass(
            flat_id=pass_in.flat_id,
            resident_id=resident_id,
            name=pass_in.name,
            phone=pass_in.phone,
            visitor_type=pass_in.visitor_type,
            pass_code=pass_code,
            vehicle_number=pass_in.vehicle_number,
            expected_arrival=pass_in.expected_arrival,
            valid_until=valid_until,
            status="active",
        )
        db.add(db_pass)
        try:
            await db.commit()
            await db.refresh(db_pass)
            return db_pass
        except IntegrityError:
            await db.rollback()
            continue
            
    raise RuntimeError("Failed to generate a unique visitor passcode after 10 attempts.")


async def get_visitor_pass_by_code(db: AsyncSession, code: str) -> VisitorPass | None:
    result = await db.execute(select(VisitorPass).where(VisitorPass.pass_code == code))
    return result.scalar_one_or_none()


async def get_visitor_passes_by_resident(
    db: AsyncSession, 
    resident_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0
) -> list[VisitorPass]:
    result = await db.execute(
        select(VisitorPass)
        .where(VisitorPass.resident_id == resident_id)
        .order_by(VisitorPass.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def log_visitor_entry(
    db: AsyncSession, log_in: VisitorLogCreate, security_guard_id: uuid.UUID
) -> VisitorLog | None:
    # Case 1: Checking in with a passcode (pre-approved or daily help)
    if log_in.pass_code:
        # Check VisitorPasses first
        result_pass = await db.execute(
            select(VisitorPass).where(
                VisitorPass.pass_code == log_in.pass_code, 
                VisitorPass.status == "active"
            )
        )
        v_pass = result_pass.scalar_one_or_none()
        
        if v_pass:
            # Mark pass as used
            v_pass.status = "used"
            
            db_log = VisitorLog(
                visitor_pass_id=v_pass.id,
                flat_id=v_pass.flat_id,
                name=v_pass.name,
                phone=v_pass.phone,
                visitor_type=v_pass.visitor_type,
                vehicle_number=v_pass.vehicle_number or log_in.vehicle_number,
                purpose="Pre-approved visit",
                entry_time=datetime.now(timezone.utc),
                entered_gate_by_id=security_guard_id,
            )
            db.add(db_log)
            await db.commit()
            await db.refresh(db_log)
            return db_log
            
        # Check DailyHelp next
        result_help = await db.execute(
            select(DailyHelp)
            .where(DailyHelp.pass_code == log_in.pass_code, DailyHelp.is_active == True)
            .options(selectinload(DailyHelp.flats))
        )
        d_help = result_help.scalar_one_or_none()
        
        if d_help:
            # Daily help visits multiple flats. Pick the first assigned flat, or fallback if flat_id specified
            flat_id = log_in.flat_id or (d_help.flats[0].id if d_help.flats else None)
            if not flat_id:
                return None  # Help is not linked to any flat
                
            db_log = VisitorLog(
                flat_id=flat_id,
                name=d_help.name,
                phone=d_help.phone,
                visitor_type="daily_help",
                vehicle_number=log_in.vehicle_number,
                purpose=f"Daily help ({d_help.role}) entry",
                entry_time=datetime.now(timezone.utc),
                entered_gate_by_id=security_guard_id,
            )
            db.add(db_log)
            await db.commit()
            await db.refresh(db_log)
            return db_log
            
        return None  # Code not found or inactive
        
    # Case 2: Manual walk-in entry (e.g. delivery boy without passcode)
    if not log_in.flat_id or not log_in.name or not log_in.phone:
        return None  # Missing details for manual entry
        
    db_log = VisitorLog(
        flat_id=log_in.flat_id,
        name=log_in.name,
        phone=log_in.phone,
        visitor_type=log_in.visitor_type,
        vehicle_number=log_in.vehicle_number,
        purpose=log_in.purpose,
        entry_time=datetime.now(timezone.utc),
        entered_gate_by_id=security_guard_id,
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log


async def log_visitor_exit(
    db: AsyncSession, log_id: uuid.UUID, security_guard_id: uuid.UUID
) -> VisitorLog | None:
    result = await db.execute(select(VisitorLog).where(VisitorLog.id == log_id))
    db_log = result.scalar_one_or_none()
    
    if db_log and not db_log.exit_time:
        db_log.exit_time = datetime.now(timezone.utc)
        db_log.exited_gate_by_id = security_guard_id
        await db.commit()
        await db.refresh(db_log)
        return db_log
        
    return None


async def get_active_gate_logs(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[VisitorLog]:
    result = await db.execute(
        select(VisitorLog)
        .where(VisitorLog.exit_time == None)
        .order_by(VisitorLog.entry_time.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_gate_logs_history(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[VisitorLog]:
    result = await db.execute(
        select(VisitorLog)
        .order_by(VisitorLog.entry_time.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_daily_help(db: AsyncSession, help_in: DailyHelpCreate) -> DailyHelp:
    for attempt in range(10):
        # Generate unique 6-digit recurring passcode starting with DH
        pass_code = "DH" + "".join([str(random.randint(0, 9)) for _ in range(4)])
        
        help_id = uuid.uuid4()
        db_help = DailyHelp(
            id=help_id,
            name=help_in.name,
            phone=help_in.phone,
            role=help_in.role,
            pass_code=pass_code,
            is_active=True,
        )
        db.add(db_help)
        
        # Assign flats
        for f_id in help_in.flat_ids:
            association = DailyHelpFlat(daily_help_id=help_id, flat_id=f_id)
            db.add(association)
            
        try:
            await db.commit()
            await db.refresh(db_help, ["flats"])
            return db_help
        except IntegrityError:
            await db.rollback()
            continue
            
    raise RuntimeError("Failed to generate a unique daily help passcode after 10 attempts.")


async def get_all_daily_helps(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[DailyHelp]:
    result = await db.execute(
        select(DailyHelp)
        .options(selectinload(DailyHelp.flats))
        .order_by(DailyHelp.name)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
