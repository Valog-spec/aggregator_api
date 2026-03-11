import asyncio
import logging

from src.models import Outbox
from src.notification.base import CapashinoClient
from src.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Воркер для обработки и отправки уведомлений из outbox таблицы."""

    def __init__(
        self,
        outbox_repo: OutboxRepository,
        capashino_client: CapashinoClient,
        max_retries: int = 3,
        batch_size: int = 100,
        poll_interval: int = 5,
    ):
        """
        Инициализация воркера outbox.

        Args:
            outbox_repo: Репозиторий для работы с outbox таблицей
            capashino_client: Клиент для отправки уведомлений в Capashino
            max_retries: Максимальное количество попыток отправки (по умолчанию 3)
            batch_size: Размер пачки сообщений для обработки (по умолчанию 100)
            poll_interval: Интервал опроса БД в секундах (по умолчанию 5)
        """
        self._outbox_repo = outbox_repo
        self.client = capashino_client
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """Запускает бесконечный цикл обработки outbox сообщений."""
        self.running = True
        logger.info("Воркер outbox запущен")
        while self.running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Остановка воркера"""
        self.running = False
        logger.info("Воркер outbox остановлен")

    async def _process_batch(self):
        """Обрабатывает одну пачку outbox сообщений в рамках одной транзакции."""
        messages = await self._outbox_repo.get_pending_messages(
            limit=self.batch_size, max_retries=self.max_retries
        )

        if not messages:
            return

        logger.info(f"Обработка пачки из {len(messages)} outbox сообщений")

        for msg in messages:
            await self._process_message(msg)

        await self._outbox_repo.commit()
        logger.info(f"Пачка из {len(messages)} сообщений закоммичена")

    async def _process_message(self, msg: Outbox):
        """Обрабатывает одно outbox сообщение."""
        try:
            response = await self.client.send_notification(
                message=msg.payload.get("notification_text"),
                reference_id=msg.payload.get("ticket_id"),
                idempotency_key=str(msg.id),
            )

            if response:
                await self._outbox_repo.mark_as_sent(msg.id)
                logger.info(f"Сообщение {msg.id} успешно отправлено в Capashino")
            else:
                await self._outbox_repo.increment_retry(msg.id, "Temporary error")
                logger.warning(
                    f"Сообщение {msg.id} временно не отправлено, "
                    f"попытка {msg.retry_count + 1}/{self.max_retries}"
                )

        except Exception as e:
            await self._outbox_repo.increment_retry(msg.id, str(e))
            logger.error(f"Ошибка при отправке сообщения {msg.id}: {e}")
