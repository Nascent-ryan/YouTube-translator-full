from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    default_output_dir: Path
    cookies_path: Path | None

    @classmethod
    def load(cls) -> "AppConfig":
        load_dotenv()

        output_dir = Path(os.getenv("DEFAULT_OUTPUT_DIR", "outputs")).expanduser()
        cookies_value = os.getenv(
            "YTDLP_COOKIES_PATH",
            str(Path.cwd() / "cookies.txt"),
        ).strip()
        cookies_path = Path(cookies_value).expanduser() if cookies_value else None

        return cls(default_output_dir=output_dir, cookies_path=cookies_path)
