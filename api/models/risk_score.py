import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    score_type: Mapped[str] = mapped_column(String(64))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    risk_level: Mapped[str] = mapped_column(String(16))
    model_version: Mapped[str | None] = mapped_column(String(32))
    features: Mapped[dict | None] = mapped_column(JSONB)
    explanation: Mapped[list | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"))
