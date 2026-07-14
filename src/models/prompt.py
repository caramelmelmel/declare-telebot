import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Prompt(Base):
    __tablename__ = "prompt"
    __table_args__ = (UniqueConstraint("telegram_update_id", name="uq_prompt_telegram_update_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.telegram_user_id"))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    telegram_update_id: Mapped[int] = mapped_column(BigInteger)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    content: Mapped[str] = mapped_column(Text)
    raw_payload_object_key: Mapped[str] = mapped_column(String)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
