import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class EventStatus(str, enum.Enum):
    """Статус события (значения из Events Provider API)."""

    new = "new"
    published = "published"


class Event(Base):
    """
    Событие

    Attributes:
        id: Уникальный идентификатор (UUID).
        name: Название события.
        event_time: Дата и время проведения (с временной зоной).
        registration_deadline: Дедлайн регистрации (с временной зоной).
        place_id: FK на площадку проведения.
        status: Текущий статус события (new / published).
        number_of_visitors: Количество зарегистрированных участников.
        place: Связанная площадка.
        tickets: Выданные билеты на это событие.
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id"), nullable=False
    )
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), nullable=False, default=EventStatus.new
    )
    number_of_visitors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    place: Mapped["Place"] = relationship("Place", back_populates="events")  # noqa: F821
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="event")  # noqa: F821
