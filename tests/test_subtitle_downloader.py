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
