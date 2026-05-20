import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, RoleChecker
from app.crud import notices as crud_notices
from app.models.users import User
from app.schemas.notices import NoticeOut, NoticeCreate, VoteOut, VoteCreate

router = APIRouter()

# Role checks
admin_required = RoleChecker(["admin"])


@router.post("", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def publish_notice(payload: NoticeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Publish a new notice. If type is 'poll', options must be specified. Only admin can create polls."""
    # Only admin, resident, and tenant can post notices
    if current_user.role not in ["admin", "resident", "tenant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to publish notices",
        )
        
    if payload.type == "poll":
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create interactive polls",
            )
        if not payload.poll_options or len(payload.poll_options) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A poll notice must include at least 2 options",
            )
    return await crud_notices.create_notice(db, payload, current_user.id)


@router.get("", response_model=List[NoticeOut])
async def list_active_notices(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Retrieve all active (unexpired) notices."""
    return await crud_notices.get_all_notices(db, limit=limit, offset=offset)


@router.get("/{notice_id}", response_model=NoticeOut)
async def get_notice_by_id(notice_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve full details of a specific notice and its voting counts if it is a poll."""
    notice = await crud_notices.get_notice(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@router.post("/{notice_id}/vote", response_model=VoteOut)
async def cast_vote(
    notice_id: uuid.UUID,
    payload: VoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cast a vote on a poll notice. Only allows one vote per user per poll."""
    # Verify notice exists and is a poll
    notice = await crud_notices.get_notice(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if notice.type != "poll":
        raise HTTPException(status_code=400, detail="This notice is not a voting poll")
        
    # Verify option belongs to this notice
    option_ids = [opt.id for opt in notice.poll_options]
    if payload.option_id not in option_ids:
        raise HTTPException(status_code=400, detail="Invalid option for this poll notice")
        
    vote = await crud_notices.vote_poll_option(db, notice_id, payload.option_id, current_user.id)
    if not vote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already voted on this poll notice",
        )
        
    return vote
