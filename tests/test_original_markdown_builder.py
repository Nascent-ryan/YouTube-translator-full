from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.original_markdown_builder import OriginalMarkdownBuilder
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v11 import VttConverter


def test_original_markdown_builder_creates_english_markdown_when_available() -> None:
    tmp_path = Path(".pytest_local") / f"original_md_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "sample.ko.vtt"
    en_vtt = tmp_path / "sample.en.vtt"
    ko_vtt.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n안녕하세요.\n", encoding="utf-8")
    en_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello there.

00:00:03.000 --> 00:00:05.000
This is the original English transcript.
""",
        encoding="utf-8",
    )

    builder = OriginalMarkdownBuilder()
    markdown = builder.build(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="origmdtest",
                url="https://www.youtube.com/watch?v=origmdtest",
                title="Original Builder Test",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt, en_vtt],
        ),
        VttConverter(),
    )

    assert markdown is not None
    assert "# Original Builder Test (English Original)" in markdown
    assert "## English Transcript" in markdown
    assert "Hello there." in markdown
