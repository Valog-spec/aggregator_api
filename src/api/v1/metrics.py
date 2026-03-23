from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, generate_latest

from src.dependencies import EventRepoDep
from src.middleware.metrics_definitions import events_total

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics(repo: EventRepoDep):
    """Энпоинт отдачи метрик"""
    count = await repo.get_count()
    events_total.set(count)
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain",
    )
