"""Load CLI configuration from config.yaml with environment overrides."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from config.settings import Settings, settings

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


@dataclass(frozen=True)
class CLIConfig:
    report_format: str
    language: str
    default_standard: str
    sessions_dir: Path
    standards_root: Path
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None

    @classmethod
    def load(
        cls,
        *,
        config_path: Path | None = None,
        env: Settings | None = None,
        project_root: Path | None = None,
    ) -> CLIConfig:
        env = env or settings
        project_root = project_root or Path(__file__).resolve().parent.parent
        path = config_path or CONFIG_PATH

        file_data: dict = {}
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                file_data = yaml.safe_load(handle) or {}

        sessions_dir = Path(file_data.get("sessions_dir", "sessions"))
        standards_root = Path(file_data.get("standards_root", "standards"))
        if not sessions_dir.is_absolute():
            sessions_dir = project_root / sessions_dir
        if not standards_root.is_absolute():
            standards_root = project_root / standards_root

        return cls(
            report_format=str(file_data.get("report_format", "pdf")),
            language=str(file_data.get("language", "english")),
            default_standard=str(file_data.get("default_standard", "ASME_B31.3")),
            sessions_dir=sessions_dir,
            standards_root=standards_root,
            openai_api_key=env.openai_api_key,
            openai_model=env.openai_model,
            openai_base_url=env.openai_base_url,
        )
