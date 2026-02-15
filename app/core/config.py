from pydantic import BaseModel
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    upload_dir: str = "uploads"
    max_upload_bytes: int = 50 * 1024 * 1024
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    smtp_from: str | None = None
    frontend_base_url: str = "http://localhost:8080"
    mongo_uri: str | None = None
    mongo_db_health: str = "Health"
    mongo_collection_imhe: str = "IMHE"
    mongo_db_pollution: str = "Pollution"
    mongo_collection_openaq: str = "OpenAQ"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        database_url = os.getenv("DATABASE_URL", "")
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        if not jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY is not set")
        _settings = Settings(
            database_url=database_url,
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expires_minutes=int(os.getenv("JWT_EXPIRES_MINUTES", "60")),
            upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_pass=os.getenv("SMTP_PASS"),
            smtp_from=os.getenv("SMTP_FROM"),
            frontend_base_url=os.getenv("FRONTEND_BASE_URL", "http://localhost:8080"),
            mongo_uri=os.getenv("MONGO_URI"),
            mongo_db_health=os.getenv("MONGO_DB_HEALTH", "Health"),
            mongo_collection_imhe=os.getenv("MONGO_COLLECTION_IMHE", "IMHE"),
            mongo_db_pollution=os.getenv("MONGO_DB_POLLUTION", "Pollution"),
            mongo_collection_openaq=os.getenv("MONGO_COLLECTION_OPENAQ", "OpenAQ"),
        )
    return _settings
