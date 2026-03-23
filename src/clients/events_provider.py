"""HTTP-клиент внешнего провайдера событий на базе httpx."""

import logging
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from src.clients.metrics_transport import create_http_client
from src.configs.config import settings

logger = logging.getLogger(__name__)


class HttpxEventsProviderClient:
    """Реализация EventsProviderClient через httpx.AsyncClient.

    Обходит cursor-based пагинацию провайдера, отдавая страницы
    по одной через async generator.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        """
        Args:
            base_url: Базовый URL провайдера (без завершающего слеша).
            api_key: Ключ аутентификации (заголовок X-Api-Key).
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        """Вернуть заголовки для аутентификации."""
        return {"X-Api-Key": self._api_key}

    async def iter_pages(
        self, changed_at: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Итерировать страницы событий, обходя cursor-пагинацию провайдера.

        Каждая итерация отдаёт одну страницу сразу после получения,
        не накапливая весь список в памяти.

        Args:
            changed_at: Фильтр по дате изменения. При первой синхронизации
                передаётся ``"2000-01-01"`` для загрузки всех событий.

        Yields:
            Список событий текущей страницы.

        Raises:
            httpx.HTTPStatusError: При ответе с кодом 4xx/5xx.
        """
        first_url: str = f"{self._base_url}/api/events/"
        params: dict[str, str] = {}
        if changed_at:
            params["changed_at"] = changed_at

        async with create_http_client(headers=self._headers()) as client:
            logger.debug("Запрос первой страницы: %s params=%s", first_url, params)
            response = await client.get(first_url, params=params)
            response.raise_for_status()
            data = response.json()
            page_results = data.get("results", [])
            logger.debug("Первая страница: получено %d событий", len(page_results))
            yield page_results
            next_url = data.get("next")
            page_num = 2
            while next_url:
                parsed = urlparse(next_url)
                next_url = self._base_url + parsed.path
                if parsed.query:
                    next_url += f"?{parsed.query}"
                response = await client.get(next_url)
                response.raise_for_status()

                if "cursor" in next_url and "cursor" not in str(response.url):
                    logger.warning(
                        "Cursor-URL перенаправлен на %s — пагинация завершена",
                        response.url,
                    )
                    break
                data = response.json()
                page_results = data.get("results", [])
                logger.debug(
                    "Страница %d: получено %d событий", page_num, len(page_results)
                )
                yield page_results
                next_url = data.get("next")
                page_num += 1
                if next_url and "cursor" not in next_url:
                    logger.warning(
                        "Следующая страница без cursor, остановка: %s", next_url
                    )
                    next_url = None

    async def get_seats(self, event_id: str) -> list[str]:
        """
        Запросить доступные места для события.

        Args:
            event_id: Строковый UUID события.

        Returns:
            Список идентификаторов мест, например ``["A1", "A3"]``.

        Raises:
            httpx.HTTPStatusError: При ответе с кодом 4xx/5xx.
        """
        async with create_http_client(headers=self._headers()) as client:
            logger.debug("Запрос мест для события %s", event_id)
            response = await client.get(
                f"{self._base_url}/api/events/{event_id}/seats/"
            )
            response.raise_for_status()
            data = response.json()
            seats = data.get("seats", [])
            logger.debug("Получено %d мест для события %s", len(seats), event_id)
            return seats

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        """
        Зарегистрировать участника на событие у провайдера.

        Args:
            event_id: UUID события.
            first_name: Имя участника.
            last_name: Фамилия участника.
            email: Email участника.
            seat: Номер места.

        Returns:
            ticket_id, выданный провайдером.

        Raises:
            httpx.HTTPStatusError: 400 если место занято, 404 если событие не найдено.
        """
        async with create_http_client(headers=self._headers()) as client:
            logger.debug("Регистрация на событие %s, место %s", event_id, seat)
            response = await client.post(
                f"{self._base_url}/api/events/{event_id}/register/",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
            )
            response.raise_for_status()
            ticket_id = response.json()["ticket_id"]
            logger.info(
                "Регистрация успешна: event=%s seat=%s ticket=%s",
                event_id,
                seat,
                ticket_id,
            )
            return ticket_id

    async def unregister(self, event_id: str, ticket_id: str) -> None:
        """
        Отменить регистрацию участника у провайдера.

        Args:
            event_id: UUID события.
            ticket_id: Идентификатор билета, выданный провайдером.

        Raises:
            httpx.HTTPStatusError: 404 если событие или билет не найдены.
        """
        async with create_http_client(headers=self._headers()) as client:
            logger.debug("Отмена регистрации: event=%s ticket=%s", event_id, ticket_id)
            response = await client.request(
                "DELETE",
                f"{self._base_url}/api/events/{event_id}/unregister/",
                json={"ticket_id": ticket_id},
            )
            response.raise_for_status()
            logger.info("Регистрация отменена: event=%s ticket=%s", event_id, ticket_id)


def get_events_provider_client() -> HttpxEventsProviderClient:
    """Создать клиент провайдера с настройками из конфига."""
    return HttpxEventsProviderClient(
        base_url=settings.EVENTS_PROVIDER_BASE_URL,
        api_key=settings.EVENTS_PROVIDER_API_KEY,
    )
