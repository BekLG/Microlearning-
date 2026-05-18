from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    FREE_TRIAL_DOCUMENTS: int
    MAX_FILE_SIZE_MB: int
    MAX_PAGES_PER_DOC: int
    MAX_PDF_PAGES: int = 50
    MAX_PPTX_SLIDES: int = 50
    MAX_DOCX_WORDS: int = 12000
    MAX_CHUNKS: int
    MAX_CHARS_PER_CHUNK: int = 1800
    FACTS_PER_CHUNK: int
    MCQ_INTERVAL: int
    AI_TIMEOUT_SECONDS: int
    MAX_RETRIES: int
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str
    OPENROUTER_FALLBACK_MODELS: str = ""
    OPENROUTER_MAX_429_WAIT_SECONDS: int = 30
    OPENROUTER_SITE_URL: str | None = None
    OPENROUTER_APP_NAME: str | None = None
    SECRET_KEY: str
    DATABASE_URL: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_INITDATA_MAX_AGE_SECONDS: int = 300
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for security")
        if v == "changeme-secret-key":
            raise ValueError("SECRET_KEY must be changed from default value")
        return v

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
