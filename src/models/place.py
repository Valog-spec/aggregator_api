import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Place(Base):
    """
    Площадка проведения событий.

    Attributes:
        id: Уникальный идентификатор площадки (UUID).
        name: Название площадки.
        city: Город расположения.
        address: Полный адрес.
        seats_pattern: Схема расположения мест (необязательно).
        events: Связанные события.
    """

    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    seats_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship("Event", back_populates="place")  # noqa: F821
