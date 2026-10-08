from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

MB = 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./geospatial.db"

    max_upload_size_mb: int = 50
    max_zip_files: int = 100
    max_uncompressed_size_mb: int = 500
    max_compression_ratio: int = 100

    debug: bool = False

    @property
    def max_uncompressed_bytes(self) -> int:
        return self.max_uncompressed_size_mb * MB


@lru_cache
def get_settings() -> Settings:
    return Settings()
