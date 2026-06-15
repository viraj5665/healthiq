import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fhir_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True)
    clinical_status: Mapped[str | None] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(String(64))
    code_system: Mapped[str | None] = mapped_column(String(128))
    display: Mapped[str | None] = mapped_column(String(512))
    category: Mapped[str | None] = mapped_column(String(64))
    onset_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abatement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
