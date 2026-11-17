from typing import Annotated
from app.clients.orders import CoreOrderClient
from app.core.s3_client import S3AsyncService, get_s3_async_client
from fastapi import Depends
from app.core.database import get_async_session
from app.repositories import DocumentAsyncRepository
from app.services import DocumentService
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings


security = HTTPBearer()

class CurrentUser(BaseModel):
    id: UUID

def get_core_order_client(request: Request) -> CoreOrderClient:
    return CoreOrderClient(
        client=request.app.state.http_client,
        base_url=settings.DRF_CORE_URL,
    )

CoreOrderClientDep = Annotated[CoreOrderClient, Depends(get_core_order_client)]
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]

async def verify_order_access(
    order_id: UUID,
    credentials: TokenDep,
    core_client: CoreOrderClientDep,
) -> UUID:
    exists = await core_client.check_order_exists(
        order_id=order_id,
        token=credentials.credentials,
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден или у вас нет к нему доступа.",
        )
    return order_id


def get_current_user_unverified(credentials: TokenDep) -> CurrentUser:
    try:
        payload = jwt.decode(
            credentials.credentials,
            options={"verify_signature": False},
        )
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="В токене отсутствует user_id.",
            )
        return CurrentUser(id=user_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный формат токена.",
        )


VerifiedOrderDep = Annotated[UUID, Depends(verify_order_access)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_unverified)]

async def get_document_repository(db_session: Annotated[AsyncSession, Depends(get_async_session)]):
    return DocumentAsyncRepository(db_session)

async def get_document_service(
    repository: Annotated[DocumentAsyncRepository, Depends(get_document_repository)],
    s3_client: Annotated[S3AsyncService, Depends(get_s3_async_client)],
    core_client: CoreOrderClientDep
    ):
    return DocumentService(repository, core_client, s3_client)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]