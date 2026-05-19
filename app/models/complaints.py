import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    raised_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")  # plumbing, electricity, security, lift, housekeeping, parking, other
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")  # low, medium, high, emergency
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")  # open, assigned, in_progress, resolved, closed
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="complaints")
    raised_by: Mapped["User"] = relationship("User", foreign_keys=[raised_by_id], back_populates="raised_complaints")
    assigned_to: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_complaints")
    comments: Mapped[list["ComplaintComment"]] = relationship("ComplaintComment", back_populates="complaint", cascade="all, delete-orphan")


class ComplaintComment(Base):
    __tablename__ = "complaint_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="comments")
