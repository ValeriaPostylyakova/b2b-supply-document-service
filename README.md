# Documents Service

Микросервис управления документами для B2B-платформы. Сервис работает рядом с основным приложением (Core): получает события о подтверждении заказов, асинхронно формирует PDF-счета, сохраняет файлы в S3-совместимое хранилище и предоставляет авторизованный доступ к документам.

## Возможности

- Генерация PDF-счетов на основе события `order.confirmed`.
- Асинхронная обработка задач через Celery.
- Хранение метаданных документов в PostgreSQL, файлов — в S3/MinIO.
- Выдача временных pre-signed URL для скачивания.
- Проверка существования и доступности заказа через Core с передачей Bearer-токена пользователя.
- Получение документов заказа через REST API.

## Архитектура и взаимодействие

```text
                  Core service
                 /            \
       order.confirmed         HTTP: check order access
              |                         ^
              v                         |
       RabbitMQ (topic)          Documents API
              |                         |
       Documents Consumer                |
              |                         |
        Celery task                     |
              |                         |
       +------+-------+-----------------+
       |              |                 |
   PostgreSQL       S3 / MinIO        Redis
   metadata          PDF files      cache / Celery
```

**Сценарий генерации:** Core публикует `order.confirmed` в exchange `b2b.events`. Consumer принимает сообщение из очереди `documents.events`, валидирует payload и передает задачу `documents.generate_invoice` в Celery. Worker рендерит HTML-шаблон счета в PDF, загружает файл в S3 и сохраняет метаданные в PostgreSQL.

**Сценарий чтения:** клиент вызывает `GET /api/v1/documents/{order_id}` с Bearer-токеном. Documents Service обращается к Core для проверки доступа к заказу, получает метаданные документов и формирует короткоживущие ссылки на скачивание.

Redis и RabbitMQ используются как общая инфраструктура с Core. PostgreSQL с метаданными документов разворачивается отдельно для этого сервиса.

## Технологии

- Python 3.12, FastAPI, Pydantic
- SQLAlchemy 2.x, Alembic, PostgreSQL
- RabbitMQ, aio-pika, Celery, Redis
- S3 API, aioboto3, boto3 (MinIO или совместимое хранилище)
- Jinja2, WeasyPrint
- Docker, Docker Compose

## REST API

После запуска документация OpenAPI доступна здесь:

- Swagger UI: `http://localhost:8002/docs`
- ReDoc: `http://localhost:8002/redoc`
- OpenAPI JSON: `http://localhost:8002/openapi.json`

### `GET /api/v1/documents/{order_id}`

Возвращает документы заказа и временные ссылки на скачивание. Доступ к заказу проверяется в Core.

**Заголовок:**

```http
Authorization: Bearer <access_token>
```

**Пример ответа `200 OK`:**

```json
[
  {
    "order_id": "4c5b9c1a-ff1b-4f3e-a2a0-7b6d9f1e2a10",
    "document_type": "invoice",
    "original_name": "Счет-заказ №1042.pdf",
    "created_at": "2026-11-13T09:36:23Z",
    "download_url": "https://storage.example.com/..."
  }
]
```

Если документов пока нет, сервис возвращает пустой массив `[]`.

Основные ошибки: `401` — отсутствует или отклонен токен; `403` — нет доступа к организации; `404` — заказ не найден или недоступен; `502`/`503`/`504` — ошибка взаимодействия с Core.

### Health check

`GET /health` — liveness-проверка HTTP-приложения. Возвращает `{"status":"ok"}` и не проверяет доступность внешних зависимостей.

## Запуск

### Требования

- Docker и Docker Compose
- Запущенная инфраструктура Core: RabbitMQ и Redis
- Доступный S3/MinIO и созданный bucket
- Сеть Docker `shared_rabbitmq_net`, к которой подключены RabbitMQ, Redis и сервис

### Конфигурация

Создайте локальный `.env` на основе примера:

```bash
cp .env.example .env
```

Заполните учетные данные PostgreSQL, RabbitMQ и S3, а также адрес Core и endpoints хранилища. Не коммитьте `.env` и реальные секреты в репозиторий.

Убедитесь, что общая сеть создана (если ее еще не создал Core):

```bash
docker network create shared_rabbitmq_net
```

Имена `core_rabbitmq_broker`, `core_redis_broker` и `minio` должны разрешаться внутри подключенной Docker-сети. При необходимости измените их в `.env`.

### Сборка и запуск

```bash
docker compose build
docker compose up -d
```

Примените миграции:

```bash
docker compose exec documents-service alembic upgrade head
```

Проверьте состояние контейнеров и API:

```bash
docker compose ps
curl http://localhost:8002/health
```

Swagger: `http://localhost:8002/docs`.

Для просмотра логов:

```bash
docker compose logs -f documents-service documents-consumer documents-worker
```

Остановка:

```bash
docker compose down
```

Данные PostgreSQL хранятся в Docker volume `documents_db_data`. Команда `docker compose down -v` удалит volume с данными — используйте ее только если действительно хотите удалить базу.

## Контракт события RabbitMQ

Consumer слушает durable topic exchange `b2b.events`, очередь `documents.events` и routing key `order.confirmed`.

Payload соответствует `InvoiceGeneratePayload`:

```json
{
  "order": {
    "id": "4c5b9c1a-ff1b-4f3e-a2a0-7b6d9f1e2a10",
    "order_number": "1042",
    "status": "confirmed",
    "created_at": "2026-11-13T09:00:00Z",
    "updated_at": "2026-11-13T09:30:00Z",
    "supplier": {"name": "Поставщик"},
    "buyer": {"name": "Покупатель"},
    "items_count": 1,
    "total_amount": "12500.00"
  },
  "items": [
    {
      "product": {"name": "Товар", "sku": "SKU-001"},
      "warehouse": {"name": "Склад", "address": "Адрес склада"},
      "quantity": 2,
      "unit_price": "6250.00",
      "line_total": "12500.00"
    }
  ]
}
```

В AMQP-сообщении тип события должен быть `order.confirmed` (поле `type`; при его отсутствии используется routing key). Consumer валидирует данные до постановки Celery-задачи.

## Структура проекта

```text
app/
├── api/v1/endpoints/   # HTTP endpoints
├── clients/            # HTTP-клиенты Core
├── core/               # конфигурация, БД, Redis, S3, Celery
├── schemas/            # Pydantic-схемы и контракт события
├── templates/          # HTML-шаблоны документов
├── consumer.py         # RabbitMQ consumer
├── tasks.py            # Celery tasks
├── models.py           # SQLAlchemy models
├── repositories.py     # доступ к данным
└── services.py         # бизнес-логика
migrations/             # Alembic migrations
Dockerfile
docker-compose.yml
```

## Примечания по эксплуатации

- Ссылки на скачивание создаются с ограниченным сроком действия (по умолчанию 5 минут).
- Уникальность документа обеспечивается ограничением на пару `order_id` + `document_type`.
- Worker использует отдельную Redis DB для Celery result backend; API использует Redis DB, заданную `REDIS_DB`.
- Для production следует использовать отдельные секреты и TLS/HTTPS на внешнем ingress/reverse proxy, настроить резервное копирование PostgreSQL и S3, а также мониторинг очередей и Celery worker.
- Перед публикацией проекта замените демонстрационные значения конфигурации и убедитесь, что в репозитории нет приватных ключей, токенов и реальных паролей.

## Статус

Проект подготовлен к контейнерному запуску в составе инфраструктуры Core. Для полноценного production rollout необходимо подставить реальные параметры окружения, проверить совместимость контрактов Core и обеспечить доступность общей инфраструктуры.
