from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import SubtitleDocument, VideoMetadata
from youtube_translator_desktop.services.markdown_exporter import MarkdownExporter


def test_export_writes_markdown_file() -> None:
    tmp_path = Path(".pytest_local") / f"exporter_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    subtitle_document = SubtitleDocument(
        metadata=VideoMetadata(
            video_id="abcdefghijk",
            url="https://www.youtube.com/watch?v=abcdefghijk",
            title="테스트 영상",
            channel_name="Channel",
            language_code="en",
        ),
        vtt_path=tmp_path / "abcdefghijk.en.vtt",
        markdown_text="# 테스트 영상\n\n## 자막 정리본\n- hello world",
        plain_text="hello world",
        segment_count=3,
    )

    exporter = MarkdownExporter()
    output_path, markdown = exporter.export(subtitle_document, tmp_path)

    assert output_path.exists()
    assert "## 자막 정리본" in markdown
