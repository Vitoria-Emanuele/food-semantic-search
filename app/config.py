import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    DATA_PATH: str = "data/dados_limpos.json"
    TOP_K: int = 3
    MIN_SCORE: float = 0.0
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """Converte a string de origens separada por vírgula em uma lista."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
