import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class SyncStatus(str, enum.Enum):
    """Статус последней операции синхронизации."""

    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"


class SyncMeta(Base):
    """
    Метаданные синхронизации с внешним провайдером.

    В таблице хранится единственная строка (id=1), обновляемая при каждом запуске.

    Attributes:
        id: Первичный ключ, всегда равен 1.
        last_sync_time: Время последнего успешного запуска синхронизации.
        last_changed_at: Максимальная метка изменения среди загруженных событий.
            Используется как фильтр при следующем запросе к провайдеру.
        sync_status: Текущий статус синхронизации.
        error_message: Сообщение об ошибке последней неудачной попытки.
    """

    __tablename__ = "sync_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sync_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus), nullable=False, default=SyncStatus.idle
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
