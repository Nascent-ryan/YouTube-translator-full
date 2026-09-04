from pathlib import Path

from youtube_translator_desktop.config import AppConfig


def test_config_loads_default_cookies_path(monkeypatch) -> None:
    monkeypatch.delenv("DEFAULT_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("YTDLP_COOKIES_PATH", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")
    monkeypatch.delenv("TRANSLATION_PROVIDER", raising=False)

    config = AppConfig.load()

    assert config.default_output_dir == Path("outputs")
    assert config.cookies_path == Path.cwd() / "cookies.txt"
    assert config.translation_provider == "youtube"


def test_config_prefers_openai_when_api_key_exists(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.delenv("TRANSLATION_PROVIDER", raising=False)

    config = AppConfig.load()

    assert config.openai_api_key == "test-key"
    assert config.openai_model == "gpt-5-mini"
    assert config.translation_provider == "openai"


def test_config_uses_explicit_cookie_path(monkeypatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_PATH", "/etc/secrets/youtube-cookies.txt")

    config = AppConfig.load()

    assert config.cookies_path == Path("/etc/secrets/youtube-cookies.txt")
