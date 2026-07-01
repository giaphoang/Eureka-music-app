from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://eureka:eureka@db:5432/eureka_music"
    audio_root: Path = Path("/data/audio")
    max_upload_bytes: int = 50 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
