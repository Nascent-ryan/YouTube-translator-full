from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v8 import VttConverter


def test_vtt_converter_v8_groups_natural_paragraphs_without_qa_labels() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v8_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "paragraphs.ko.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:05.000
최근 GitHub 다운로드 실패가 자주 보였습니다.

00:00:06.000 --> 00:00:11.000
저희도 계속 추적하고 있는데 실제로 실패 빈도가 꽤 올라갔습니다.

00:00:12.000 --> 00:00:17.000
마이크로소프트가 남는 CPU를 외부에 팔면서 완충 여유가 크게 줄었습니다.

00:00:30.000 --> 00:00:35.000
CPU 수요는 에이전트 워크로드와 강화학습 루프 때문에 빠르게 늘고 있습니다.

00:00:36.000 --> 00:00:41.000
추론 클러스터 운영도 그만큼 더 빡빡해지고 있습니다.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="paragraphv8",
                url="https://www.youtube.com/watch?v=paragraphv8",
                title="문단 정리 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt],
        )
    )

    assert "## 전체 번역 텍스트" not in document.markdown_text
    assert "**Q**" not in document.markdown_text
    assert "**A**" not in document.markdown_text
    assert "### 주제 1." in document.markdown_text
    assert "### 주제 2." in document.markdown_text
    assert "\n\n최근 GitHub 다운로드 실패가 자주 보였습니다. 저희도 계속 추적하고 있는데 실제로 실패 빈도가 꽤 올라갔습니다." in document.markdown_text
    assert "CPU 수요는 에이전트 워크로드와 강화학습 루프 때문에 빠르게 늘고 있습니다. 추론 클러스터 운영도 그만큼 더 빡빡해지고 있습니다." in document.markdown_text
