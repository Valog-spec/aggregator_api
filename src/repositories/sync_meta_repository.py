"""Репозиторий для работы с метаданными синхронизации."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sync_meta import SyncMeta, SyncStatus


class SyncMetaRepository:
    """Доступ к единственной записи метаданных синхронизации."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: Активная асинхронная сессия SQLAlchemy.
        """
        self._session = session

    async def get_or_create(self) -> SyncMeta:
        """Получить метаданные синхронизации или создать при первом запуске.

        Returns:
            Объект SyncMeta с id=1.
        """
        result = await self._session.execute(select(SyncMeta).where(SyncMeta.id == 1))
        meta = result.scalar_one_or_none()
        if meta is None:
            meta = SyncMeta(id=1, sync_status=SyncStatus.idle)
            self._session.add(meta)
            await self._session.flush()
        return meta

    async def save(self, meta: SyncMeta) -> SyncMeta:
        """Зафиксировать изменения в метаданных синхронизации.

        Args:
            meta: Изменённый объект SyncMeta.

        Returns:
            Тот же объект после flush.
        """
        await self._session.flush()
        return meta
