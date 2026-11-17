import logging
from uuid import UUID
import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class CoreOrderClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def check_order_exists(self, order_id: UUID, token: str) -> bool:
        url = f"{self.base_url}/api/v1/orders/{order_id}/exists/"
        headers = {"Authorization": f"Bearer {token}"}

        logger.info("Проверка существования заказа в ядре: order_id=%s", order_id)

        try:
            response = await self.client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            logger.error(
                "Таймаут при запросе к ядру: order_id=%s, url=%s, error=%s",
                order_id,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Ядро системы не ответило вовремя при проверке заказа.",
            )
        except httpx.RequestError as exc:
            logger.error(
                "Сетевая ошибка при запросе к ядру: order_id=%s, url=%s, error=%s",
                order_id,
                url,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ядро системы временно недоступно.",
            )

        if response.status_code == status.HTTP_200_OK:
            logger.info( "Ответ от ядра успешно получен", )
            return True

        if response.status_code == status.HTTP_404_NOT_FOUND:
            logger.warning(
                "Заказ не найден или недоступен пользователю: order_id=%s",
                order_id,
            )
            return False

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            logger.warning(
                "Ядро отклонило токен авторизации (401): order_id=%s",
                order_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен авторизации отклонен основным сервисом.",
            )

        if response.status_code == status.HTTP_403_FORBIDDEN:
            logger.warning(
                "У пользователя отсутствует организация (403): order_id=%s",
                order_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У пользователя нет привязанной организации.",
            )

        logger.error(
            "Неожиданный статус ответа от ядра: order_id=%s, status=%s, body=%s",
            order_id,
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Неожиданный ответ от ядра: {response.status_code}",
        )
