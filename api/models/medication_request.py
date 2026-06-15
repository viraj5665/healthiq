import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class MedicationRequest(Base):
    __tablename__ = "medication_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fhir_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32))
    intent: Mapped[str | None] = mapped_column(String(32))
    medication_code: Mapped[str] = mapped_column(String(64))
    medication_system: Mapped[str | None] = mapped_column(String(128))
    medication_display: Mapped[str | None] = mapped_column(String(512))
    authored_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dosage_text: Mapped[str | None] = mapped_column(Text)
    dosage_route: Mapped[str | None] = mapped_column(String(128))
    dosage_timing: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
