import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database import Base


class Ticket(Base):
    """Билет пользователя на конкретное событие.

    Attributes:
        ticket_id: Идентификатор билета, полученный от Events Provider API (PK).
        event_id: FK на событие.
        first_name: Имя участника.
        last_name: Фамилия участника.
        email: Email участника.
        seat: Номер места.
        created_at: Время создания записи (проставляется БД автоматически).
        event: Связанное событие.
    """

    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    seat: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship("Event", back_populates="tickets")  # noqa: F821
