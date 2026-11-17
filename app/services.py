import asyncio
from uuid import UUID

from app.repositories import DocumentAsyncRepository
from app.clients.orders import CoreOrderClient
from app.core.exceptions import ApplicationError
from app.schemas.documents import DocumentsListResponse
from app.core.s3_client import S3AsyncService


class DocumentService:
    def __init__(self, repository: DocumentAsyncRepository, core_client: CoreOrderClient, s3_client: S3AsyncService):
        self.repository = repository
        self.client = core_client
        self.s3_client = s3_client
        
    async def _build_document_response(self, doc) -> DocumentsListResponse:
        url = await self.s3_client.get_download_url(
            storage_key=doc.storage_key,
            original_name=doc.original_name,
        )
        return DocumentsListResponse(
            order_id=doc.order_id,
            document_type=doc.document_type,
            original_name=doc.original_name,
            created_at=doc.created_at,
            download_url=url,
        )

    async def get_documents_by_order_id(self, order_id: UUID, token: str):
        order_exists = await self.client.check_order_exists(
            order_id=order_id,
            token=token,
        )
        
        if not order_exists:
            raise ApplicationError(
                status_code=404,
                detail='Заказ не найден или у вашей организации нет к нему доступа.'
            )
                
        documents = await self.repository.get_documents_by_order_id(order_id)
        
        items = await asyncio.gather(
            *(self._build_document_response(doc) for doc in documents)
        )
        return list(items)
    
    

