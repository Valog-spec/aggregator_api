from fastapi import APIRouter, BackgroundTasks

from src.schemas.sync import SyncTriggered

router = APIRouter(prefix="/sync", tags=["sync"])


async def _run_sync() -> None:
    """Запустить синхронизацию в фоне с собственной сессией БД."""
    from src.cache.redis_cache import get_seats_cache
    from src.clients.events_provider import get_events_provider_client
    from src.database import async_session_factory
    from src.repositories.event_repository import EventRepository
    from src.repositories.sync_meta_repository import SyncMetaRepository
    from src.use_cases.sync_use_cases import SyncEventsUseCase

    async with async_session_factory() as session:
        use_case = SyncEventsUseCase(
            event_repo=EventRepository(session),
            sync_meta_repo=SyncMetaRepository(session),
            provider_client=get_events_provider_client(),
            seats_cache=get_seats_cache(),
        )
        await use_case.execute()


@router.post("/trigger", response_model=SyncTriggered)
async def trigger_sync(background_tasks: BackgroundTasks) -> SyncTriggered:
    """Запустить синхронизацию событий с провайдером в фоне.

    Возвращает 200 немедленно; синхронизация выполняется асинхронно
    через FastAPI BackgroundTasks.
    """
    background_tasks.add_task(_run_sync)
    return SyncTriggered()
