from typing import Protocol


class CapashinoClient(Protocol):
    """Интерфейс для взаимодействия с серивсом уведомления."""

    async def send_notification(self): ...
