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

    # Azure Document Intelligence
    DOC_INTEL_ENDPOINT: Optional[str] = None
    DOC_INTEL_KEY: Optional[str] = None
    DOC_INTEL_API_VERSION: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)

settings = Settings()