#backend/config/settings.py
"""
Settings configuration for ProyectoSOC backend.
Carga variables de entorno y define parámetros globales para la aplicación.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    """Configuración de variables globales y secretos para la app."""
    DATABASE_URL: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str | None = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str | None = None

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_INDEX_NAME: str = os.getenv("REDIS_INDEX_NAME", "embeddings_idx")
    EMBEDDING_SCORE_THRESHOLD: float = float(os.getenv("EMBEDDING_SCORE_THRESHOLD", "0.75"))

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        case_sensitive=False,
    )

def get_settings() -> Settings:
    """Devuelve una instancia de Settings con la configuración cargada."""
    return Settings()



