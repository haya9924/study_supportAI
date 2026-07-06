"""アプリ設定 (環境変数 + 既定値)。"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # データ保存先 (SQLite DB / アップロード原本 / ページ画像)
    data_dir: Path = Path(os.environ.get("DATA_DIR", "./data")).resolve()

    # LLM モックモード: 1 なら外部通信せず決め打ち応答を返す
    llm_mock: bool = os.environ.get("LLM_MOCK", "0") in ("1", "true", "True")

    # DB に未設定の場合に使う初期 LLM 設定
    default_api_base_url: str = os.environ.get(
        "OPENAI_BASE_URL", "https://openrouter.ai/api/v1"
    )
    default_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    default_vision_model: str = os.environ.get(
        "VISION_MODEL", "google/gemini-2.5-flash"
    )
    default_text_model: str = os.environ.get("TEXT_MODEL", "google/gemini-2.5-flash")

    # OCR 変換パラメータ
    pdf_render_dpi: int = int(os.environ.get("PDF_RENDER_DPI", "150"))
    image_max_edge: int = int(os.environ.get("IMAGE_MAX_EDGE", "1600"))
    max_pages_per_material: int = int(os.environ.get("MAX_PAGES_PER_MATERIAL", "100"))
    ocr_concurrency: int = int(os.environ.get("OCR_CONCURRENCY", "3"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "study.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def pages_dir(self) -> Path:
        return self.data_dir / "pages"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.pages_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
