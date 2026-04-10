from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v2 import VttConverter


def test_vtt_converter_parses_and_renders_markdown() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    vtt_path = tmp_path / "sample.vtt"
    vtt_path.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello there

00:00:05.000 --> 00:00:07.000
This is a test
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="abcdefghijk",
                url="https://www.youtube.com/watch?v=abcdefghijk",
                title="샘플 영상",
                channel_name="Sample Channel",
                language_code="en",
            ),
            vtt_path=vtt_path,
            related_vtt_paths=[vtt_path],
        )
    )

    assert document.segment_count == 2
    assert "## 영상 정보" in document.markdown_text
    assert "`00:00:00.000` Hello there" in document.markdown_text
