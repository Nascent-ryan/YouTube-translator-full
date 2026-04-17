from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    default_output_dir: Path
    cookies_path: Path | None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    translation_provider: str = "youtube"

    @classmethod
    def load(cls) -> "AppConfig":
        load_dotenv()

        output_dir = Path(os.getenv("DEFAULT_OUTPUT_DIR", "outputs")).expanduser()
        cookies_value = os.getenv(
            "YTDLP_COOKIES_PATH",
            str(Path.cwd() / "cookies.txt"),
        ).strip()
        cookies_path = Path(cookies_value).expanduser() if cookies_value else None
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
        openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
        provider_value = os.getenv("TRANSLATION_PROVIDER", "").strip().lower()
        translation_provider = provider_value or ("openai" if openai_api_key else "youtube")

        return cls(
            default_output_dir=output_dir,
            cookies_path=cookies_path,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            translation_provider=translation_provider,
        )
