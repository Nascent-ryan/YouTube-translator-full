from fastapi.testclient import TestClient

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
    assert "CACHE_NAME" in sw_response.text
    assert 'addEventListener("fetch"' in sw_response.text

    icon_response = client.get("/icon.svg")
    assert icon_response.status_code == 200
    assert "<svg" in icon_response.text
