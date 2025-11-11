import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Gate Pass Management API"

    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "gatepass_db")

    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", "media")
    PHOTO_DIR: str = "photos"
    QR_DIR: str = "qr"

    class Config:
        env_file = ".env"


settings = Settings()
