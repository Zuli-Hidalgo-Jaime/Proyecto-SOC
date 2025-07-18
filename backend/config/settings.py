from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str | None = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        case_sensitive=False,    # opcional
    )

def get_settings() -> Settings:
    return Settings()



