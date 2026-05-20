import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.complaints import Complaint, ComplaintComment
from app.schemas.complaints import ComplaintCreate, ComplaintUpdate, CommentCreate


async def create_complaint(db: AsyncSession, complaint_in: ComplaintCreate, user_id: uuid.UUID) -> Complaint:
    db_complaint = Complaint(
        flat_id=complaint_in.flat_id,
        raised_by_id=user_id,
        title=complaint_in.title,
        description=complaint_in.description,
        category=complaint_in.category,
        priority=complaint_in.priority,
        attachment_url=complaint_in.attachment_url,
        status="open",
    )
    db.add(db_complaint)
    await db.commit()
    await db.refresh(db_complaint, ["comments"])
    return db_complaint


async def get_complaint(db: AsyncSession, complaint_id: uuid.UUID) -> Complaint | None:
    query = (
        select(Complaint)
        .where(Complaint.id == complaint_id)
        .options(selectinload(Complaint.comments))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_complaints(
    db: AsyncSession,
    flat_id: uuid.UUID | None = None,
    raised_by_id: uuid.UUID | None = None,
    assigned_to_id: uuid.UUID | None = None,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[Complaint]:
    query = select(Complaint).options(selectinload(Complaint.comments))
    if flat_id:
        query = query.where(Complaint.flat_id == flat_id)
    if raised_by_id:
        query = query.where(Complaint.raised_by_id == raised_by_id)
    if assigned_to_id:
        query = query.where(Complaint.assigned_to_id == assigned_to_id)
    if status:
        query = query.where(Complaint.status == status)
    if category:
        query = query.where(Complaint.category == category)
    if priority:
        query = query.where(Complaint.priority == priority)
        
    query = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_complaint(
    db: AsyncSession, db_complaint: Complaint, complaint_in: ComplaintUpdate
) -> Complaint:
    if complaint_in.status is not None:
        db_complaint.status = complaint_in.status
    if complaint_in.priority is not None:
        db_complaint.priority = complaint_in.priority
    if complaint_in.assigned_to_id is not None:
        db_complaint.assigned_to_id = complaint_in.assigned_to_id
    await db.commit()
    await db.refresh(db_complaint)
    return db_complaint


async def create_complaint_comment(
    db: AsyncSession, comment_in: CommentCreate, user_id: uuid.UUID, complaint_id: uuid.UUID
) -> ComplaintComment:
    db_comment = ComplaintComment(
        complaint_id=complaint_id,
        user_id=user_id,
        comment=comment_in.comment,
        attachment_url=comment_in.attachment_url,
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment
