import asyncio
import json
import uuid

import aio_pika

from app.core.config import settings
import logging
from app.tasks import generate_order_invoice_task
from app.schemas.invoice import InvoiceGeneratePayload
from pydantic import ValidationError
    
logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    try:
       
        event_type = message.type or message.routing_key
        raw_event = json.loads(message.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Некорректный JSON в сообщении: %s", exc)
        await message.reject(requeue=False)
        return

    if event_type == "order.confirmed":
        try:
            validated_payload = InvoiceGeneratePayload(**raw_event)
        
            task = generate_order_invoice_task.delay(
                validated_payload.model_dump(mode="json")
            )
            logger.info(
                "Задача генерации счета отправлена в Celery (task_id=%s, order_id=%s)",
                task.id,
                validated_payload.order.id,
            )
        except ValidationError as exc:
            logger.error("Ошибка валидации данных заказа: %s", exc)
            await message.reject(requeue=False)
            return
    else:
        logger.warning("Неподдерживаемый тип события: %s", event_type)

    await message.ack()


async def main():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            "b2b.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        queue = await channel.declare_queue(
           settings.QUEUE_NAME,
            durable=True,
        )

        await queue.bind(exchange, routing_key="order.confirmed")

        print("Documents Service started")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                try:
                    await process_message(message)

                except Exception as exc:
                    print("Consumer error:", exc)
                    if not message.processed:
                        await message.reject(requeue=False)


if __name__ == "__main__":
    asyncio.run(main())