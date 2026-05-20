import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Boolean, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class VisitorPass(Base):
    __tablename__ = "visitor_passes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    resident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    visitor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="guest")  # guest, delivery, service, other
    pass_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # 6-digit code or unique token
    vehicle_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expected_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, used, expired, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="visitor_passes")
    resident: Mapped["User"] = relationship("User", back_populates="visitor_passes")
    logs: Mapped[list["VisitorLog"]] = relationship("VisitorLog", back_populates="visitor_pass")


class VisitorLog(Base):
    __tablename__ = "visitor_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visitor_pass_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visitor_passes.id", ondelete="SET NULL"), nullable=True)
    flat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    visitor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="guest")  # guest, delivery, service, daily_help, other
    vehicle_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(250), nullable=True)  # e.g., "Amazon", "Maid service"
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_gate_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    exited_gate_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    visitor_pass: Mapped[VisitorPass | None] = relationship("VisitorPass", back_populates="logs")
    flat: Mapped["Flat"] = relationship("Flat", back_populates="visitor_logs")


class DailyHelp(Base):
    __tablename__ = "daily_helps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # Maid, Driver, Cook, Gardener, etc.
    pass_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    # Relationships
    flats: Mapped[list["Flat"]] = relationship("Flat", secondary="daily_help_flats", back_populates="daily_helps")


class DailyHelpFlat(Base):
    __tablename__ = "daily_help_flats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    daily_help_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_helps.id", ondelete="CASCADE"), nullable=False)
    flat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("daily_help_id", "flat_id", name="uq_daily_help_flat"),
    )
