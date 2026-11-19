from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="super_secret_key_12345")
    DRF_CORE_URL: str = Field(default="http://django-server:8000")
    
    JWT_SECRET_KEY: str = Field(default='')

    DB_USER: str = Field(default="DB")
    DB_PASSWORD: str = Field(default="DB")
    DB_HOST: str = Field(default="db")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="retro_streamer")

    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=1)
    
    S3_KEY_ID: str = Field(default="minioadmin")
    S3_SECRET: str = Field(default="minioadmin")
    
    S3_INTERNAL_URL: str = Field(default="http://minio:9000")
    S3_EXTERNAL_URL: str = Field(default="http://localhost:9000")

    S3_BUCKET_NAME: str = Field(default="b2b-supply-core-private")
    
    RABBITMQ_HOST: str = Field(default='localhost')
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default='guest')
    RABBITMQ_PASSWORD: str = Field(default='guest')
    
    EXCHANGE_NAME: str = Field(default='b2b.events')
    QUEUE_NAME: str = Field(default="documents.events")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
