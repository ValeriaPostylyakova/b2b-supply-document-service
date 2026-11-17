from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.models import Document, DocumentType

class DocumentAsyncRepository:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_documents_by_order_id(self, order_id: UUID) -> list[Document]:
        stmt = select(Document).where(Document.order_id == order_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

class DocumentSyncRepository:
    def __init__(self, db_session):
        self.session = db_session

    def exists_by_order_and_type(
        self, order_id: UUID, doc_type: DocumentType
    ) -> bool:
        stmt = select(Document.id).where(
            Document.order_id == order_id,
            Document.document_type == doc_type.value,
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None
    
    def create_document(
        self,
        order_id: UUID,
        doc_type: DocumentType,
        storage_key: str,
        original_name: str,
        content_type: str,
        size: int,
    ) -> Document:
        doc = Document(
            order_id=order_id,
            document_type=doc_type.value,
            storage_key=storage_key,
            original_name=original_name,
            content_type=content_type,
            size=size,
        )
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc
    