"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_files(*, project_root: Path | None = None) -> None:
    """Load `.env` files from the repo root and desktopApp folder when present."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    root = project_root or Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
    for env_path in (root / ".env", root / "desktopApp" / ".env"):
        if env_path.is_file():
            load_dotenv(env_path, override=False)


load_env_files()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    standards_root: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            openai_base_url=os.environ.get("OPENAI_BASE_URL"),
            standards_root=os.environ.get("STANDARDS_ROOT", "knowledge/standards"),
        )


settings = Settings.from_env()
