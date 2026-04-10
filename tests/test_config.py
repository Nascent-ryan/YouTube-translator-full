from pathlib import Path

from youtube_translator_desktop.config import AppConfig


def test_config_loads_default_cookies_path(monkeypatch) -> None:
    monkeypatch.delenv("DEFAULT_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("YTDLP_COOKIES_PATH", raising=False)

    config = AppConfig.load()

    assert config.default_output_dir == Path("outputs")
    assert config.cookies_path == Path.cwd() / "cookies.txt"
