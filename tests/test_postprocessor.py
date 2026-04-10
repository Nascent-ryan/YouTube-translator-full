from pathlib import Path

from youtube_translator_desktop.models import SubtitleDocument, VideoMetadata
from youtube_translator_desktop.services.postprocessor_v2 import PostProcessor


def test_postprocessor_converts_to_note_style() -> None:
    processor = PostProcessor()
    document = SubtitleDocument(
        metadata=VideoMetadata(
            video_id="abcdefghijk",
            url="https://www.youtube.com/watch?v=abcdefghijk",
            title="테스트",
            channel_name="채널",
            language_code="ko",
        ),
        vtt_path=Path("sample.vtt"),
        markdown_text=(
            "# 테스트\n\n"
            "## 한국어 전체 번역 정리\n"
            "- `00:00:01.000` 이 부분은 정말 중요합니다.\n"
            "  원문: \"This part matters a lot.\"\n"
            "## 인상적인 원문 표현\n"
            "- `00:00:01.000` \"This part matters a lot.\"\n"
            "  - 번역: 이 부분은 정말 중요합니다.\n"
        ),
        plain_text="이 부분은 정말 중요합니다.",
        segment_count=1,
    )

    processed = processor.process(document)

    assert "## 한국어 전체 번역 정리" in processed.markdown_text
    assert "중요함" in processed.markdown_text
    assert "정말" not in processed.markdown_text
