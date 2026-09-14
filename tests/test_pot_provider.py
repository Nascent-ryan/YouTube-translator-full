from pathlib import Path

from youtube_translator_desktop.services.pot_provider import PotProviderProcess


def test_provider_script_path_uses_render_build_location(monkeypatch) -> None:
    monkeypatch.delenv("YTDLP_POT_PROVIDER_SCRIPT", raising=False)
    monkeypatch.delenv("BGUTIL_PROVIDER_VERSION", raising=False)

    assert PotProviderProcess._script_path() == (
        Path.cwd()
        / ".render"
        / "bgutil-ytdlp-pot-provider-2.0.0"
        / "server"
        / "build"
        / "main.js"
    )


def test_provider_script_path_accepts_override(monkeypatch) -> None:
    script = Path("provider") / "main.js"
    monkeypatch.setenv("YTDLP_POT_PROVIDER_SCRIPT", str(script))

    assert PotProviderProcess._script_path() == script
