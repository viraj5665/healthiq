import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    report_markdown: Mapped[str] = mapped_column(Text)
    summary_data: Mapped[dict] = mapped_column(JSONB)
    model_version: Mapped[str | None] = mapped_column(String(64))
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
