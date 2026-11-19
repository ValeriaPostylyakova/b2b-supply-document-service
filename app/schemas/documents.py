from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models import DocumentType
from app.schemas.base import BaseResponse


class DocumentsListResponse(BaseResponse):
    order_id: UUID = Field(description="Идентификатор заказа.")
    document_type: DocumentType = Field(description="Тип документа.")
    original_name: str = Field(description="Исходное имя файла.")
    created_at: datetime = Field(description="Дата и время создания документа.")
    download_url: str = Field(description="Временная ссылка для скачивания файла.")
