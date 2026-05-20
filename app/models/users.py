import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="resident")  # admin, resident, tenant, security, staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vehicle_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )

    # Relationships
    owned_flats: Mapped[list["Flat"]] = relationship("Flat", foreign_keys="Flat.owner_id", back_populates="owner")
    rented_flats: Mapped[list["Flat"]] = relationship("Flat", foreign_keys="Flat.tenant_id", back_populates="tenant")
    raised_complaints: Mapped[list["Complaint"]] = relationship("Complaint", foreign_keys="Complaint.raised_by_id", back_populates="raised_by")
    assigned_complaints: Mapped[list["Complaint"]] = relationship("Complaint", foreign_keys="Complaint.assigned_to_id", back_populates="assigned_to")
    comments: Mapped[list["ComplaintComment"]] = relationship("ComplaintComment", back_populates="user")
    created_notices: Mapped[list["Notice"]] = relationship("Notice", back_populates="created_by")
    poll_votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="user")
    visitor_passes: Mapped[list["VisitorPass"]] = relationship("VisitorPass", back_populates="resident")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="paid_by")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'resident', 'tenant', 'security', 'staff')", name="chk_user_role"),
    )


class Flat(Base):
    __tablename__ = "flats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    block: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "A", "B"
    flat_number: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "101", "1204"
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )

    # Relationships
    owner: Mapped[User | None] = relationship("User", foreign_keys=[owner_id], back_populates="owned_flats")
    tenant: Mapped[User | None] = relationship("User", foreign_keys=[tenant_id], back_populates="rented_flats")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="flat")
    complaints: Mapped[list["Complaint"]] = relationship("Complaint", back_populates="flat")
    visitor_passes: Mapped[list["VisitorPass"]] = relationship("VisitorPass", back_populates="flat")
    visitor_logs: Mapped[list["VisitorLog"]] = relationship("VisitorLog", back_populates="flat")
    daily_helps: Mapped[list["DailyHelp"]] = relationship("DailyHelp", secondary="daily_help_flats", back_populates="flats")

    __table_args__ = (
        UniqueConstraint("block", "flat_number", name="uq_block_flat_number"),
    )

