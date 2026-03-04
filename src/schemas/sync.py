from pydantic import BaseModel


class SyncTriggered(BaseModel):
    """Ответ при успешном запуске фоновой синхронизации."""

    status: str = "sync triggered"
