from youtube_translator_desktop.web_main import _pot_provider_enabled


def test_pot_provider_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_YTDLP_POT_PROVIDER", raising=False)

    assert not _pot_provider_enabled()


def test_pot_provider_can_be_enabled_explicitly(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_YTDLP_POT_PROVIDER", "true")

    assert _pot_provider_enabled()
