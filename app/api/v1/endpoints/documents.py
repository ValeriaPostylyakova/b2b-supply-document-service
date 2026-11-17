from typing import Annotated
from uuid import UUID

from app.dependencies import CurrentUserDep, DocumentServiceDep, TokenDep, VerifiedOrderDep, get_document_service
from fastapi import APIRouter, Depends
from app.services import DocumentService
from app.schemas.documents import DocumentsListResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.get("/{order_id}", response_model=list[DocumentsListResponse])
async def get_order_documents(
    order_id: UUID,
    credentials: TokenDep,
    document_service: DocumentServiceDep,
):
    documents = await document_service.get_documents_by_order_id(
        order_id=order_id,
        token=credentials.credentials,
    )
    return documents
    