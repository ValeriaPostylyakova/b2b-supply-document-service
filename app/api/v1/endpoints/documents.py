from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import DocumentServiceDep, TokenDep
from app.schemas.documents import DocumentsListResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.get(
    "/{order_id}",
    response_model=list[DocumentsListResponse],
    summary="Получить документы заказа",
    description=(
        "Возвращает список документов заказа и временные ссылки на скачивание. "
        "Доступ к заказу дополнительно проверяется в основном сервисе."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Отсутствует или недействителен Bearer-токен."},
        status.HTTP_403_FORBIDDEN: {"description": "У пользователя нет доступа к организации."},
        status.HTTP_404_NOT_FOUND: {"description": "Заказ не найден или недоступен."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Основной сервис вернул неожиданный ответ."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Основной сервис временно недоступен."},
        status.HTTP_504_GATEWAY_TIMEOUT: {"description": "Истекло время ожидания ответа основного сервиса."},
    },
)
async def get_order_documents(
    order_id: UUID,
    credentials: TokenDep,
    document_service: DocumentServiceDep,
) -> list[DocumentsListResponse]:
    """Получить документы заказа, доступного текущему пользователю."""
    return await document_service.get_documents_by_order_id(
        order_id=order_id,
        token=credentials.credentials,
    )
