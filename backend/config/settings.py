from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # original en mayúsculas
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    # alias minúscula (no rompe nada)
    database_url: str | None = Field(None, alias="DATABASE_URL")

    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str | None = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

def get_settings() -> Settings:
    return Settings()


