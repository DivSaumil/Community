import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notices import Notice, PollOption, PollVote
from app.schemas.notices import NoticeCreate, NoticeUpdate


async def create_notice(db: AsyncSession, notice_in: NoticeCreate, admin_id: uuid.UUID) -> Notice:
    db_notice = Notice(
        title=notice_in.title,
        content=notice_in.content,
        type=notice_in.type,
        expires_at=notice_in.expires_at,
        created_by_id=admin_id,
    )
    db.add(db_notice)
    await db.flush()  # Get notice ID before commit
    
    if notice_in.type == "poll" and notice_in.poll_options:
        for opt_text in notice_in.poll_options:
            db_option = PollOption(notice_id=db_notice.id, option_text=opt_text)
            db.add(db_option)
            
    await db.commit()
    await db.refresh(db_notice, ["poll_options"])
    return db_notice


async def get_notice(db: AsyncSession, notice_id: uuid.UUID) -> Notice | None:
    query = (
        select(Notice)
        .where(Notice.id == notice_id)
        .options(selectinload(Notice.poll_options))
    )
    res = await db.execute(query)
    notice = res.scalar_one_or_none()
    if not notice:
        return None
        
    # Populate vote counts dynamically in a single query
    if notice.poll_options:
        option_ids = [opt.id for opt in notice.poll_options]
        vote_res = await db.execute(
            select(PollVote.option_id, func.count(PollVote.id))
            .where(PollVote.option_id.in_(option_ids))
            .group_by(PollVote.option_id)
        )
        vote_counts = {opt_id: count for opt_id, count in vote_res.all()}
        for opt in notice.poll_options:
            opt.vote_count = vote_counts.get(opt.id, 0)
        
    return notice


async def get_all_notices(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> list[Notice]:
    query = (
        select(Notice)
        .where((Notice.expires_at == None) | (Notice.expires_at > datetime.now(timezone.utc)))
        .options(selectinload(Notice.poll_options))
        .order_by(Notice.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    notices = list(result.scalars().all())
    
    # Populate vote counts dynamically in a single query
    option_ids = [opt.id for notice in notices for opt in notice.poll_options]
    if option_ids:
        vote_res = await db.execute(
            select(PollVote.option_id, func.count(PollVote.id))
            .where(PollVote.option_id.in_(option_ids))
            .group_by(PollVote.option_id)
        )
        vote_counts = {opt_id: count for opt_id, count in vote_res.all()}
    else:
        vote_counts = {}
        
    for notice in notices:
        for opt in notice.poll_options:
            opt.vote_count = vote_counts.get(opt.id, 0)
            
    return notices


async def vote_poll_option(
    db: AsyncSession, notice_id: uuid.UUID, option_id: uuid.UUID, user_id: uuid.UUID
) -> PollVote | None:
    # 1. Check if user already voted on this notice
    voted_query = select(PollVote).where(PollVote.notice_id == notice_id, PollVote.user_id == user_id)
    res = await db.execute(voted_query)
    if res.scalar_one_or_none():
        return None  # Already voted
        
    # 2. Register vote
    db_vote = PollVote(
        notice_id=notice_id,
        option_id=option_id,
        user_id=user_id,
    )
    db.add(db_vote)
    await db.commit()
    await db.refresh(db_vote)
    return db_vote


async def update_notice(
    db: AsyncSession, notice_id: uuid.UUID, notice_in: NoticeUpdate
) -> Notice | None:
    notice = await get_notice(db, notice_id)
    if not notice:
        return None
    if notice_in.title is not None:
        notice.title = notice_in.title
    if notice_in.content is not None:
        notice.content = notice_in.content
    if notice_in.expires_at is not None:
        notice.expires_at = notice_in.expires_at
    await db.commit()
    await db.refresh(notice)
    return notice


async def delete_notice(db: AsyncSession, notice_id: uuid.UUID) -> bool:
    notice = await get_notice(db, notice_id)
    if not notice:
        return False
    await db.delete(notice)
    await db.commit()
    return True

