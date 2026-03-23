"""Точка входа приложения: создание FastAPI-приложения, lifespan и подключение роутеров."""

import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.events import router as events_router
from src.api.v1.health import router as health_router
from src.api.v1.metrics import router as metrics_router
from src.api.v1.sync import router as sync_router
from src.api.v1.tickets import router as tickets_router
from src.logger.config import dict_config
from src.middleware.metrics import MetricsMiddleware
from src.notification.capashino_client import get_сapashino_client
from src.repositories.outbox_repository import OutboxRepository
from src.workers.outbox_worker import OutboxWorker

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


async def _outbox_worker_loop():
    """Бесконечный цикл воркера outbox"""
    from src.database import async_session_factory

    try:
        async with async_session_factory() as session:
            worker_outbox = OutboxWorker(
                outbox_repo=OutboxRepository(session),
                capashino_client=get_сapashino_client(),
            )
            logger.info("Запуск фонового воркера outbox")
            await worker_outbox.start()
    except asyncio.CancelledError:
        logger.info("Воркер outbox получил сигнал остановки")
        raise
    except Exception as e:
        logger.exception(f"Критическая ошибка воркера outbox: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения.

    При старте запускает фоновую задачу ежедневной синхронизации.
    При завершении корректно отменяет задачу и закрывает Redis-соединение.
    """
    from src.cache.redis_cache import redis_client

    task = asyncio.create_task(_daily_sync_loop())
    outbox_task = asyncio.create_task(_outbox_worker_loop())
    logger.info("Фоновые задачи запущены: синхронизация (24ч) и outbox (5с)")
    try:
        yield
    finally:
        task.cancel()
        outbox_task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass
        if redis_client is not None:
            await redis_client.aclose()


app = FastAPI(title="Aggregator API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)

app.include_router(health_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(metrics_router)
