import logging
from uuid import UUID
from celery.exceptions import SoftTimeLimitExceeded
from jinja2 import Environment, FileSystemLoader
from app.schemas.invoice import InvoiceGeneratePayload
from weasyprint import HTML

from app.core.celery_app import celery_app
from app.core.database import sync_session_maker
from app.core.s3_client import get_s3_sync_client
from app.models import DocumentType
from app.repositories import DocumentSyncRepository
from app.core.templates import jinja_env

logger = logging.getLogger(__name__)


def _cleanup_s3_file(s3_client, storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        s3_client.delete_object(storage_key)
        logger.info("Откат S3: файл %s успешно удален", storage_key)
    except Exception:
        logger.error(
            "Критично: не удалось удалить файл %s из S3 при откате",
            storage_key,
            exc_info=True,
        )


@celery_app.task(
    name="documents.generate_invoice",
    bind=True,
    autoretry_for=(IOError, ConnectionError),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    soft_time_limit=60,
    time_limit=75,
)
def generate_order_invoice_task(self, payload: dict) -> str | None:  
    data = InvoiceGeneratePayload.model_validate(payload)
    
    order_id = UUID(data.order.id)
    order_number = data.order.order_number
    logger.info("Старт генерации счета для заказа #%s", order_number)

    s3_client = get_s3_sync_client()
    uploaded_storage_key: str | None = None

    with sync_session_maker() as session:
        repo = DocumentSyncRepository(session)
        try:
            if repo.exists_by_order_and_type(order_id, DocumentType.INVOICE):
                logger.warning(
                    "Счет для заказа #%s уже существует. Пропуск.", order_number
                )
                return None

            template = jinja_env.get_template("orders/invoice_template.html")
            html_string = template.render(**payload)

            pdf_bytes = HTML(string=html_string).write_pdf()
            if pdf_bytes is None:
                raise ValueError(f"Не удалось сгенерировать PDF для заказа #{order_number}")

            storage_key = f"invoices/invoice_{order_id}.pdf"
            original_name = f"Счет-заказ №{order_number}.pdf"

            s3_client.upload_document(
                file_bytes=pdf_bytes,
                storage_key=storage_key,
                content_type="application/pdf",
            )
            uploaded_storage_key = storage_key

            doc = repo.create_document(
                order_id=order_id,
                doc_type=DocumentType.INVOICE,
                storage_key=storage_key,
                original_name=original_name,
                content_type="application/pdf",
                size=len(pdf_bytes),
            )

            session.commit()

            logger.info("Счет для заказа #%s готов. Doc ID: %s", order_number, doc.id)
            return str(doc.id)

        except SoftTimeLimitExceeded:
            session.rollback()
            _cleanup_s3_file(s3_client, uploaded_storage_key)
            logger.error("Таймаут генерации PDF для заказа #%s", order_number)
            return None

        except Exception as exc:
            session.rollback()
            _cleanup_s3_file(s3_client, uploaded_storage_key)
            logger.error("Ошибка генерации счета для #%s", order_number, exc_info=True)
            raise exc
