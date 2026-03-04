"""Точка входа приложения: создание FastAPI-приложения, lifespan и подключение роутеров."""

import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.events import router as events_router
from src.api.v1.health import router as health_router
from src.api.v1.sync import router as sync_router
from src.api.v1.tickets import router as tickets_router
from src.logger.config import dict_config

logging.config.dictConfig(dict_config)
logger = logging.getLogger(__name__)


async def _daily_sync_loop() -> None:
    """Бесконечный цикл фоновой синхронизации событий."""
    from src.cache.redis_cache import get_seats_cache
    from src.clients.events_provider import get_events_provider_client
    from src.database import async_session_factory
    from src.repositories.event_repository import EventRepository
    from src.repositories.sync_meta_repository import SyncMetaRepository
    from src.use_cases.sync_use_cases import SyncEventsUseCase

    while True:
        try:
            async with async_session_factory() as session:
                use_case = SyncEventsUseCase(
                    event_repo=EventRepository(session),
                    sync_meta_repo=SyncMetaRepository(session),
                    provider_client=get_events_provider_client(),
                    seats_cache=get_seats_cache(),
                )
                await use_case.execute()
            logger.info("Ежедневная синхронизация завершена успешно")
        except Exception:
            logger.exception("Ежедневная синхронизация завершилась с ошибкой")

        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения.

    При старте запускает фоновую задачу ежедневной синхронизации.
    При завершении корректно отменяет задачу и закрывает Redis-соединение.
    """
    from src.cache.redis_cache import redis_client

    task = asyncio.create_task(_daily_sync_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await redis_client.aclose()


app = FastAPI(title="Aggregator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
