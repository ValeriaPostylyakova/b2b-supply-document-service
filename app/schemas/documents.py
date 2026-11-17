from datetime import datetime
from uuid import UUID
from pydantic import ValidationInfo, computed_field
from app.models import DocumentType
from app.schemas.base import BaseResponse
from app.models import DocumentType


class DocumentsListResponse(BaseResponse):
    order_id: UUID
    document_type: DocumentType
    original_name: str
    created_at: datetime
    download_url: str