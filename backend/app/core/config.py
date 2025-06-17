from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    OPENAI_API_VERSION: Optional[str] = None
    AZURE_LLM_DEPLOYMENT_NAME: Optional[str] = None
    
    # LlamaParse
    LLAMAPARSE_API_KEY: Optional[str] = None
    
    # --- NEW: Celery & Redis Settings ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)

settings = Settings()