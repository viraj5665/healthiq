import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fhir_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(64))
    code_system: Mapped[str | None] = mapped_column(String(128))
    code: Mapped[str] = mapped_column(String(64))
    display: Mapped[str | None] = mapped_column(String(256))
    value_quantity: Mapped[Decimal | None] = mapped_column(Numeric)
    value_unit: Mapped[str | None] = mapped_column(String(32))
    value_string: Mapped[str | None] = mapped_column(Text)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric)
    interpretation: Mapped[str | None] = mapped_column(String(32))
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
