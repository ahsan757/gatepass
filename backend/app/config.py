import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Gate Pass Management API"

    # MongoDB
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb+srv://Ahsan12:Ahsan12@botss.rvm4jx6.mongodb.net/")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "gatepass_db")

    # Media directories
    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", "media")
    PHOTO_DIR: str = "photos"
    QR_DIR: str = "qr"

    # NEW FIELDS (Required for QR Code functionality)
    env: str = os.getenv("ENV", "dev")
    dev_nextjs_url: str = os.getenv("DEV_NEXTJS_URL", "http://localhost:3000")
    prod_nextjs_url: str = os.getenv("PROD_NEXTJS_URL", "https://your-production-domain.com")

    class Config:
        env_file = ".env"
        extra = "ignore"   # IMPORTANT: prevents future errors from extra fields


settings = Settings()
