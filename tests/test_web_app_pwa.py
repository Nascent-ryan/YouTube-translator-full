from fastapi.testclient import TestClient

from youtube_translator_desktop.config import AppConfig
from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import BrowserSubtitleSource, SubtitleDownloader
from youtube_translator_desktop.web_app import create_app


def test_web_app_exposes_pwa_assets() -> None:
    client = TestClient(create_app())

    home_response = client.get("/")
    assert home_response.status_code == 200
    assert 'rel="manifest"' in home_response.text
    assert "/sw.js" in home_response.text
    assert 'apple-mobile-web-app-capable' in home_response.text

    manifest_response = client.get("/manifest.webmanifest")
    assert manifest_response.status_code == 200
    assert '"display": "standalone"' in manifest_response.text
    assert '"start_url": "/"' in manifest_response.text
    assert '"/icon.svg"' in manifest_response.text

    sw_response = client.get("/sw.js")
    assert sw_response.status_code == 200
    assert 'CACHE_NAME = "youtube-translator-v3"' in sw_response.text
    assert 'addEventListener("fetch"' in sw_response.text

    assert "youtubei/v1/player" in home_response.text
    assert '"Content-Type": "text/plain;charset=UTF-8"' in home_response.text
    assert 'postJson("/api/convert-vtt"' in home_response.text

    icon_response = client.get("/icon.svg")
    assert icon_response.status_code == 200
    assert "<svg" in icon_response.text


def test_prepare_returns_browser_download_source(monkeypatch, tmp_path) -> None:
    def fake_prepare(self, url: str) -> BrowserSubtitleSource:
        return BrowserSubtitleSource(
            metadata=VideoMetadata(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Sample video",
                channel_name="Sample channel",
                language_code="en-US",
            ),
            subtitle_url="https://www.youtube.com/api/timedtext?fmt=vtt",
            subtitle_format="vtt",
        )

    monkeypatch.setattr(SubtitleDownloader, "prepare_browser_download", fake_prepare)
    config = AppConfig(default_output_dir=tmp_path, cookies_path=None)
    client = TestClient(create_app(config))

    response = client.post("/api/prepare", json={"url": "https://youtu.be/dQw4w9WgXcQ"})

    assert response.status_code == 200
    assert response.json()["subtitle_format"] == "vtt"
    assert response.json()["language_code"] == "en-US"
    assert response.headers["cache-control"] == "no-store"


def test_convert_vtt_runs_existing_pipeline_without_server_download(tmp_path) -> None:
    config = AppConfig(default_output_dir=tmp_path, cookies_path=None)
    client = TestClient(create_app(config))
    vtt_text = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello from the browser.
"""

    response = client.post(
        "/api/convert-vtt",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_id": "dQw4w9WgXcQ",
            "title": "Sample video",
            "channel": "Sample channel",
            "language_code": "en-US",
            "vtt_text": vtt_text,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Sample video"
    assert payload["download_url"].startswith("/downloads/")
    assert (tmp_path / "web" / "downloads" / "dQw4w9WgXcQ.en-US.browser.vtt").exists()
