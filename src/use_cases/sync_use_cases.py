import logging
from datetime import datetime, timezone

from src.cache.base import AsyncCacheProtocol
from src.clients.base import EventsProviderClient
from src.models.sync_meta import SyncStatus
from src.repositories.event_repository import EventRepository
from src.repositories.sync_meta_repository import SyncMetaRepository

logger = logging.getLogger(__name__)


class SyncEventsUseCase:
    """Синхронизация событий из внешнего провайдера в локальную БД.

    После успешного upsert событий инвалидирует записи кеша мест
    для всех обновлённых событий, чтобы следующий запрос
    ``GET /events/{id}/seats`` получил актуальные данные от провайдера.
    """

    INITIAL_CHANGED_AT = "2000-01-01"

    def __init__(
        self,
        event_repo: EventRepository,
        sync_meta_repo: SyncMetaRepository,
        provider_client: EventsProviderClient,
        seats_cache: AsyncCacheProtocol,
    ) -> None:
        """
        Args:
            event_repo: Репозиторий событий.
            sync_meta_repo: Репозиторий метаданных синхронизации.
            provider_client: HTTP-клиент внешнего провайдера.
            seats_cache: Кеш мест для инвалидации после синхронизации.
        """
        self._event_repo = event_repo
        self._sync_meta_repo = sync_meta_repo
        self._client = provider_client
        self._seats_cache = seats_cache

    async def execute(self) -> None:
        """Запустить синхронизацию событий.

        Алгоритм:
        1. Устанавливает статус running в метаданных синхронизации.
        2. При первом запуске использует changed_at=2000-01-01 (все события).
           При повторных — last_changed_at из предыдущей синхронизации.
        3. Получает все события от провайдера (обходит cursor-пагинацию).
        4. Для каждого события выполняет upsert площадки и события.
        5. Инвалидирует кеш мест для всех синхронизированных событий.
        6. Сохраняет max(changed_at) из полученных событий как last_changed_at.
        7. Устанавливает статус success.

        При любой ошибке фиксирует статус failed и повторно бросает исключение.
        """
        meta = await self._sync_meta_repo.get_or_create()
        meta.sync_status = SyncStatus.running
        await self._sync_meta_repo.save(meta)

        try:
            if meta.last_changed_at:
                changed_at = meta.last_changed_at.date().isoformat()
                logger.debug(
                    "Инкрементальная синхронизация с changed_at=%s", changed_at
                )
            else:
                changed_at = self.INITIAL_CHANGED_AT
                logger.info(
                    "Первая синхронизация — загрузка всех событий с changed_at=%s",
                    changed_at,
                )

            total = 0
            event_ids: list[str] = []
            changed_at_values: list[str] = []

            async for page in self._client.iter_pages(changed_at=changed_at):
                for event_data in page:
                    await self._event_repo.upsert_from_provider(event_data)
                    if "id" in event_data:
                        event_ids.append(event_data["id"])
                    if event_data.get("changed_at"):
                        changed_at_values.append(event_data["changed_at"])
                total += len(page)
                await self._event_repo.commit()
                logger.debug("Страница обработана, синхронизировано событий: %d", total)

            if not event_ids:
                logger.info("Нет новых или изменённых событий")
            else:
                logger.info("Синхронизировано событий: %d", total)

            if event_ids:
                await self._seats_cache.delete_many(event_ids)
                logger.debug("Инвалидирован кеш мест для %d событий", len(event_ids))

            if changed_at_values:
                meta.last_changed_at = datetime.fromisoformat(max(changed_at_values))
                logger.debug("Обновлён last_changed_at: %s", meta.last_changed_at)

            meta.last_sync_time = datetime.now(timezone.utc)
            meta.sync_status = SyncStatus.success
            meta.error_message = None
            await self._sync_meta_repo.save(meta)
            await self._event_repo.commit()
            logger.info("Синхронизация завершена успешно, обновлено событий: %d", total)

        except Exception as exc:
            logger.error("Синхронизация завершилась с ошибкой: %s", exc)
            logger.exception("Трассировка ошибки синхронизации")
            meta.sync_status = SyncStatus.failed
            meta.error_message = str(exc)
            await self._sync_meta_repo.save(meta)
            await self._event_repo.commit()
            raise
