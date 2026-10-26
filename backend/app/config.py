import os
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
_env_file = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ulavu"
    
    # Exotel API credentials for IVR telephony & SMS integration
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_SUBDOMAIN: str = "api.exotel.com"
    EXOTEL_PHONE_NUMBER: str = ""
    
    # Test / Demo phone numbers for live notifications
    DEMO_RETAILER_SMS_PHONE: str = ""
    TEST_RETAILER_PHONE: str = ""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=(".env", str(_env_file)),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
