"""Граф зависимостей (DI) для FastAPI."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_cache import RedisTTLCache, get_seats_cache
from src.clients.events_provider import (
    HttpxEventsProviderClient,
    get_events_provider_client,
)
from src.database import async_session_factory
from src.repositories.event_repository import EventRepository
from src.repositories.outbox_repository import OutboxRepository
from src.repositories.sync_meta_repository import SyncMetaRepository
from src.repositories.ticket_repository import TicketRepository
from src.use_cases.events_use_cases import (
    GetEventDetailUseCase,
    GetEventsUseCase,
    GetSeatsUseCase,
)
from src.use_cases.sync_use_cases import SyncEventsUseCase
from src.use_cases.tickets_use_cases import CancelTicketUseCase, CreateTicketUseCase


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Создать сессию БД с автоматическим управлением транзакцией."""
    async with async_session_factory() as session:
        async with session.begin():
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_event_repo(session: SessionDep) -> EventRepository:
    """Создать репозиторий событий для текущей сессии."""
    return EventRepository(session)


def get_ticket_repo(session: SessionDep) -> TicketRepository:
    """Создать репозиторий билетов для текущей сессии."""
    return TicketRepository(session)


def get_sync_meta_repo(session: SessionDep) -> SyncMetaRepository:
    """Создать репозиторий метаданных синхронизации для текущей сессии."""
    return SyncMetaRepository(session)


def get_outbox_repo(session: SessionDep) -> OutboxRepository:
    """Создать HTTP-клиент для оптравки уведомления."""
    return OutboxRepository(session)


def get_provider_client() -> HttpxEventsProviderClient:
    """Создать HTTP-клиент внешнего провайдера событий."""
    return get_events_provider_client()


def get_cache() -> RedisTTLCache:
    """Создать экземпляр Redis-кеша мест."""
    return get_seats_cache()


EventRepoDep = Annotated[EventRepository, Depends(get_event_repo)]
TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]
SyncMetaRepoDep = Annotated[SyncMetaRepository, Depends(get_sync_meta_repo)]
ProviderClientDep = Annotated[HttpxEventsProviderClient, Depends(get_provider_client)]
OutboxRepoDep = Annotated[OutboxRepository, Depends(get_outbox_repo)]
CacheDep = Annotated[RedisTTLCache, Depends(get_cache)]


def get_get_events_use_case(event_repo: EventRepoDep) -> GetEventsUseCase:
    """Собрать use case получения списка событий."""
    return GetEventsUseCase(event_repo)


def get_get_event_detail_use_case(event_repo: EventRepoDep) -> GetEventDetailUseCase:
    """Собрать use case получения детальной информации о событии."""
    return GetEventDetailUseCase(event_repo)


def get_get_seats_use_case(
    provider_client: ProviderClientDep, cache: CacheDep
) -> GetSeatsUseCase:
    """Собрать use case получения мест с Redis-кешем."""
    return GetSeatsUseCase(provider_client, cache)


def get_create_ticket_use_case(
    ticket_repo: TicketRepoDep,
    event_repo: EventRepoDep,
    outbox_repo: OutboxRepoDep,
    provider_client: ProviderClientDep,
) -> CreateTicketUseCase:
    """Собрать use case регистрации на событие."""
    return CreateTicketUseCase(ticket_repo, event_repo, outbox_repo, provider_client)


def get_cancel_ticket_use_case(
    ticket_repo: TicketRepoDep,
    provider_client: ProviderClientDep,
) -> CancelTicketUseCase:
    """Собрать use case отмены регистрации."""
    return CancelTicketUseCase(ticket_repo, provider_client)


def get_sync_events_use_case(
    event_repo: EventRepoDep,
    sync_meta_repo: SyncMetaRepoDep,
    provider_client: ProviderClientDep,
    cache: CacheDep,
) -> SyncEventsUseCase:
    """Собрать use case синхронизации событий с инвалидацией кеша."""
    return SyncEventsUseCase(event_repo, sync_meta_repo, provider_client, cache)
