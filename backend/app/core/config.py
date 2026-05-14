from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FiberMap"
    database_url: str = "sqlite:///./fibermap.db"
    collection_interval_minutes: int = 60

    model_config = SettingsConfigDict(env_prefix="FIBERMAP_", env_file=".env", extra="ignore")


settings = Settings()
