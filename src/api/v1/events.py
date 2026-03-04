import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.dependencies import (
    get_get_event_detail_use_case,
    get_get_events_use_case,
    get_get_seats_use_case,
)
from src.models.event import EventStatus
from src.schemas.event import EventDetail, PaginatedEvents, SeatsResponse
from src.use_cases.events_use_cases import (
    GetEventDetailUseCase,
    GetEventsUseCase,
    GetSeatsUseCase,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedEvents)
async def list_events(
    request: Request,
    use_case: Annotated[GetEventsUseCase, Depends(get_get_events_use_case)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: date | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
) -> PaginatedEvents:
    """Получить постраничный список событий."""
    date_from_dt = None
    if date_from:
        from datetime import datetime, timezone

        date_from_dt = datetime(
            date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc
        )

    items, total = await use_case.execute(
        page=page, page_size=page_size, date_from=date_from_dt, status=status
    )

    base = str(request.url).split("?")[0]

    def make_url(p: int) -> str:
        parts = [f"page={p}", f"page_size={page_size}"]
        if date_from:
            parts.append(f"date_from={date_from}")
        if status:
            parts.append(f"status={status.value}")
        return f"{base}?{'&'.join(parts)}"

    next_url = make_url(page + 1) if page * page_size < total else None
    prev_url = make_url(page - 1) if page > 1 else None

    return PaginatedEvents(count=total, next=next_url, previous=prev_url, results=items)


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: uuid.UUID,
    use_case: Annotated[GetEventDetailUseCase, Depends(get_get_event_detail_use_case)],
) -> EventDetail:
    """Получить детальную информацию о событии по его UUID."""
    return await use_case.execute(event_id)


@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    event_id: uuid.UUID,
    use_case: Annotated[GetSeatsUseCase, Depends(get_get_seats_use_case)],
) -> SeatsResponse:
    """Получить список доступных мест для события.

    Результат кешируется на 30 секунд.
    """
    return await use_case.execute(event_id)
