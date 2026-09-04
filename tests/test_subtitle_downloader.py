from pathlib import Path

from youtube_translator_desktop.services.subtitle_downloader_v3 import SubtitleDownloader


def test_missing_vtt_error_keeps_ytdlp_login_diagnostic() -> None:
    downloader = SubtitleDownloader()

    message = downloader._build_missing_vtt_error(
        "ERROR: [youtube] Sign in to confirm you're not a bot"
    )

    assert "로그인" in message


def test_missing_vtt_error_keeps_ytdlp_subtitle_diagnostic() -> None:
    downloader = SubtitleDownloader()

    message = downloader._build_missing_vtt_error("WARNING: There are no subtitles for the requested languages")

    assert "자막" in message


def test_requested_format_error_explains_missing_cookie_file() -> None:
    downloader = SubtitleDownloader(cookies_path=Path("missing-cookies.txt"))

    message = downloader._build_download_error("ERROR: Requested format is not available")

    assert "쿠키" in message


def test_subtitle_downloader_uses_canonical_youtube_url() -> None:
    downloader = SubtitleDownloader()

    assert downloader._canonical_video_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_subtitle_downloader_requests_original_auto_caption() -> None:
    downloader = SubtitleDownloader()

    assert ".*-orig" in downloader.subtitle_languages


def test_rate_limit_error_is_not_reported_as_missing_subtitles() -> None:
    downloader = SubtitleDownloader()

    message = downloader._build_download_error("ERROR: HTTP Error 429: Too Many Requests")

    assert "429" in message
    assert "자막이 없습니다" not in message


def test_po_token_error_is_not_reported_as_missing_subtitles() -> None:
    downloader = SubtitleDownloader()

    message = downloader._build_download_error("WARNING: subtitles require a PO Token")

    assert "PO Token" in message
    assert "자막이 없습니다" not in message
