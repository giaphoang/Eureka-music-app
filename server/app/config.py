from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://eureka:eureka@db:5432/eureka_music"
    audio_root: Path = Path("/data/audio")
    max_upload_bytes: int = 50 * 1024 * 1024
    recommendation_enabled: bool = Field(default=False, validation_alias="EUREKA_RECOMMENDATION_ENABLED")
    recommendation_dir: Path = Field(default=Path("/app/data/recommendation"), validation_alias="EUREKA_RECOMMENDATION_DIR")
    clap_backend: str = Field(default="laion", validation_alias="EUREKA_CLAP_BACKEND")
    hf_clap_model_id: str = Field(default="laion/clap-htsat-unfused", validation_alias="EUREKA_HF_CLAP_MODEL_ID")
    hf_clap_cache_dir: Path | None = Field(default=None, validation_alias="EUREKA_HF_CLAP_CACHE_DIR")
    clap_checkpoint: Path | None = Field(
        default=Path("/models/music_audioset_epoch_15_esc_90.14.pt"),
        validation_alias="EUREKA_CLAP_CHECKPOINT",
    )
    clap_audio_model: str = Field(default="HTSAT-base", validation_alias="EUREKA_CLAP_AUDIO_MODEL")
    clap_threads: int = Field(default=4, validation_alias="EUREKA_CLAP_THREADS")
    recommendation_candidates: int = Field(default=50, validation_alias="EUREKA_RECOMMENDATION_CANDIDATES")
    mmr_lambda: float = Field(default=0.75, validation_alias="EUREKA_MMR_LAMBDA")
    max_per_artist: int = Field(default=1, validation_alias="EUREKA_MAX_PER_ARTIST")
    max_per_album: int = Field(default=1, validation_alias="EUREKA_MAX_PER_ALBUM")
    prompt_cache_size: int = Field(default=32, validation_alias="EUREKA_PROMPT_CACHE_SIZE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
