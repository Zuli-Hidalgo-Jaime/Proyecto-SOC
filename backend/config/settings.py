"""
Settings module for environment and application configuration.
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    DATABASE_URL: str
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_REDIS_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    # TODO: Add more settings as needed

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings() 