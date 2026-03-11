from typing import Optional
from uuid import uuid4

import httpx

from src.configs.config import settings
from src.schemas.capashino import CapashinoRequest


class HttpxCapashinoClient:
    """
    Реализация CapashinoClient через httpx.AsyncClient.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        """
        Args:
            base_url: Базовый URL сервиса уведомления.
            api_key: Ключ аутентификации (заголовок X-Api-Key).
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = 30

    def _headers(self) -> dict[str, str]:
        """Вернуть заголовки для аутентификации."""
        return {"Content-Type": "application/json", "X-Api-Key": self._api_key}

    async def send_notification(
        self, message: str, reference_id: str, idempotency_key: Optional[str] = None
    ):
        """
        Отправить уведомление в Capashino сервис.

        Args:
            message (str): Текст уведомления для отправки получателю.
            reference_id (str): Идентификатор ссылочной сущности (например, ticket_id).
                Используется для связывания уведомления с исходной операцией.
            idempotency_key (Optional[str]): Ключ идемпотентности для предотвращения
                дублирующих отправок.
        """
        body = CapashinoRequest(
            message=message,
            reference_id=reference_id,
            idempotency_key=idempotency_key or str(uuid4()),
        )

        async with httpx.AsyncClient(
            headers=self._headers(), follow_redirects=True, timeout=self._timeout
        ) as client:
            response = await client.post(
                f"{self._base_url}/api/notifications", json=body.model_dump()
            )
            response.raise_for_status()

            return response


def get_сapashino_client() -> HttpxCapashinoClient:
    """Создать клиент провайдера с настройками из конфига."""
    return HttpxCapashinoClient(
        base_url=settings.CAPASHINO_BASE_URL,
        api_key=settings.EVENTS_PROVIDER_API_KEY,
    )
