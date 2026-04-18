from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    MARKETS: list[str] = [
        "zh-CN", "en-US", "en-GB", "en-IN", "en-CA",
        "ja-JP", "de-DE", "fr-FR", "it-IT", "es-ES", "pt-BR",
    ]
    PROXY_URL: str = ""
    DB_PATH: str = str(PROJECT_ROOT / "data" / "dailywall.db")
    WALLPAPER_DIR: str = str(PROJECT_ROOT / "wallpaper")
    LOG_DIR: str = str(PROJECT_ROOT / "logs")
    THUMBNAIL_WIDTH: int = 200
    PREVIEW_MAX_WIDTH: int = 1920
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    def ensure_dirs(self) -> None:
        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.WALLPAPER_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
