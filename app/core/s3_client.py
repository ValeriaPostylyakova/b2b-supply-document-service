from contextlib import asynccontextmanager
from urllib.parse import quote

import aioboto3
import boto3
from mypy_boto3_s3 import S3Client

from app.core.config import settings


class S3Base:
    def __init__(self):
        self.bucket_name: str = settings.S3_BUCKET_NAME
        self.internal_endpoint_url: str = settings.S3_INTERNAL_URL
        self.external_endpoint_url: str = settings.S3_EXTERNAL_URL

    @staticmethod
    def _build_content_disposition(storage_key: str, original_name: str | None = None) -> str:
        filename = original_name or storage_key.split("/")[-1]
        encoded_filename = quote(filename)
        return f"attachment; filename*=UTF-8''{encoded_filename}"


class S3AsyncService(S3Base):
    def __init__(self):
        super().__init__()
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET,
        )

    @asynccontextmanager
    async def get_client(self, use_external: bool = False):
        endpoint_url = (
            self.external_endpoint_url if use_external else self.internal_endpoint_url
        )
        async with self.session.client("s3", endpoint_url=endpoint_url) as client:
            yield client

    async def upload_file(
        self,
        file_bytes: bytes,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        async with self.get_client(use_external=False) as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Body=file_bytes,
                ContentType=content_type,
            )
        return storage_key

    async def get_download_url(
        self,
        storage_key: str,
        original_name: str | None = None,
        expires_in: int = 300,
    ) -> str:
        content_disposition = self._build_content_disposition(storage_key, original_name)
        async with self.get_client(use_external=True) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": storage_key,
                    "ResponseContentDisposition": content_disposition,
                },
                ExpiresIn=expires_in,
            )
        return url


class S3SyncService(S3Base):
    def __init__(self):
        super().__init__()
        self._internal_client: S3Client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET,
            endpoint_url=self.internal_endpoint_url,
        )
        self._external_client: S3Client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET,
            endpoint_url=self.external_endpoint_url,
        )

    def upload_document(
        self,
        file_bytes: bytes,
        storage_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        self._internal_client.put_object(
            Bucket=self.bucket_name,
            Key=storage_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return storage_key

    def get_download_url(
        self,
        storage_key: str,
        original_name: str | None = None,
        expires_in: int = 300,
    ) -> str:
        content_disposition = self._build_content_disposition(storage_key, original_name)
        return self._external_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_key,
                "ResponseContentDisposition": content_disposition,
            },
            ExpiresIn=expires_in,
        )
        
    def delete_object(self, storage_key: str) -> None:
        self._internal_client.delete_object(
            Bucket=self.bucket_name,
            Key=storage_key,
        )


s3_async_client = S3AsyncService()
s3_sync_client = S3SyncService()


def get_s3_async_client() -> S3AsyncService:
    return s3_async_client


def get_s3_sync_client() -> S3SyncService:
    return s3_sync_client
