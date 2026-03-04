# Events Aggregator

REST API сервис-агрегатор событий на FastAPI. Служит промежуточным слоем между клиентами и внешним Events Provider API: синхронизирует события в локальную БД, добавляет фильтрацию, удобную пагинацию и кэширование мест.

## Стек

- **Python 3.12** + **FastAPI**
- **PostgreSQL 16** — хранение событий, площадок, билетов
- **Redis 7** — кэш доступных мест (TTL 30 сек)
- **SQLAlchemy 2** async + **Alembic** — ORM и миграции
- **httpx** — HTTP-клиент для Events Provider API
- **uv** — менеджер пакетов и окружения

## Архитектура

Трёхслойная чистая архитектура:

```
API (src/api/)           — HTTP, валидация, сериализация
UseCase (src/use_cases/) — бизнес-логика, не знает о FastAPI
Repository (src/repositories/) — только SQL, не знает о бизнес-правилах
```

Зависимости между слоями идут только сверху вниз. UseCase-ы получают зависимости через `__init__` (dependency injection).

## Структура проекта

```
src/
  main.py               # точка входа, lifespan, роутеры
  dependencies.py       # граф зависимостей FastAPI (Depends)
  configs/              # настройки через pydantic-settings
  database/             # async engine, Base, session factory
  logger/               # конфигурация логирования (файлы по уровням)
  models/               # SQLAlchemy модели: Place, Event, Ticket, SyncMeta
  schemas/              # Pydantic схемы запросов и ответов
  repositories/         # SQL-запросы: EventRepository, TicketRepository, SyncMetaRepository
  clients/              # HTTP-клиент Events Provider API (Protocol + httpx реализация)
  cache/                # Redis кэш с TTL (AsyncCacheProtocol + RedisTTLCache)
  use_cases/            # бизнес-логика: события, билеты, синхронизация
  api/v1/               # эндпоинты: events, tickets, sync, health
tests/
  fakes.py              # InMemoryTTLCache для тестов (без Redis)
  test_events_use_cases.py
  test_tickets_use_cases.py
  test_sync_use_cases.py
  test_health.py
alembic/                # миграции БД
```

## Запуск через Docker Compose

```bash
# Скопировать конфиг и указать API ключ
cp .env.example .env

# Запустить (БД + Redis + миграции + приложение)
docker compose up --build
```

Приложение будет доступно на `http://localhost:8000`.

## Локальный запуск

**Требования:** PostgreSQL и Redis запущены локально.

```bash
# Установить зависимости
uv sync

# Настроить окружение
cp .env.example .env

# Применить миграции
uv run alembic upgrade head

# Запустить сервер
uv run uvicorn src.main:app --reload
```

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL | `postgresql+asyncpg://user:pass@localhost:5432/aggregator` |
| `REDIS_URL` | Строка подключения к Redis | `redis://localhost:6379/0` |
| `EVENTS_PROVIDER_BASE_URL` | Базовый URL Events Provider API | `https://events-provider.dev-2.python-labs.ru` |
| `EVENTS_PROVIDER_API_KEY` | API ключ для аутентификации | `your-key-here` |

## API эндпоинты

### Health

```
GET /api/health/
```
```json
{"status": "ok"}
```

### События

```
GET /api/events/?page=1&page_size=20&date_from=2026-01-01
```
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/events/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "Концерт",
      "place": {"id": "uuid", "name": "Зал", "city": "Москва", "address": "ул. Пушкина 1"},
      "event_time": "2026-01-11T17:00:00+03:00",
      "registration_deadline": "2026-01-10T17:00:00+03:00",
      "status": "published",
      "number_of_visitors": 5
    }
  ]
}
```

```
GET /api/events/{event_id}/
```
Ответ аналогичен списку, но `place` дополнительно содержит поле `seats_pattern`.

```
GET /api/events/{event_id}/seats/
```
```json
{"event_id": "uuid", "available_seats": ["A1", "A3", "B5"]}
```
Данные берутся из Events Provider API и кэшируются на 30 секунд.

### Билеты

```
POST /api/tickets/                     → 201
```
```json
// Request
{"event_id": "uuid", "first_name": "Иван", "last_name": "Иванов", "email": "ivan@example.com", "seat": "A15"}

// Response
{"ticket_id": "1fed0122-b675-42e2-8ae7-49bfb53e8d7f"}
```

```
DELETE /api/tickets/{ticket_id}/       → 200
```
```json
{"success": true}
```

### Синхронизация

```
POST /api/sync/trigger/
```
```json
{"status": "sync triggered"}
```

Запускает синхронизацию в фоне. Также автоматически запускается раз в сутки при старте приложения.

## Синхронизация событий

- **Первый запуск:** загружает все события (`changed_at=2000-01-01`)
- **Повторные запуски:** только изменённые события (инкрементально через `max(changed_at)`)
- Обходит cursor-based пагинацию провайдера автоматически
- После синхронизации инвалидирует кэш мест для обновлённых событий
- Хранит метаданные: `last_sync_time`, `last_changed_at`, `sync_status`

## Тесты

```bash
uv run pytest tests/ -v
```

17 unit-тестов покрывают все UseCase-ы. Используют `unittest.mock` (AsyncMock) — без реальной БД и HTTP-запросов.

## Линтер

```bash
uv run ruff check .
uv run ruff format .
```
