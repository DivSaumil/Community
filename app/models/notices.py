import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="general")  # general, emergency, event, poll
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="created_notices")
    poll_options: Mapped[list["PollOption"]] = relationship("PollOption", back_populates="notice", cascade="all, delete-orphan")
    votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="notice", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    option_text: Mapped[str] = mapped_column(String(200), nullable=False)

    # Relationships
    notice: Mapped[Notice] = relationship("Notice", back_populates="poll_options")
    votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="option", cascade="all, delete-orphan")


class PollVote(Base):
    __tablename__ = "poll_votes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("poll_options.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    notice: Mapped[Notice] = relationship("Notice", back_populates="votes")
    option: Mapped[PollOption] = relationship("PollOption", back_populates="votes")
    user: Mapped["User"] = relationship("User", back_populates="poll_votes")

    __table_args__ = (
        UniqueConstraint("notice_id", "user_id", name="uq_notice_user_vote"),
    )
