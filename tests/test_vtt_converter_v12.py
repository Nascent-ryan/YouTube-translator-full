from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v12 import VttConverter


def test_vtt_converter_v12_prefers_noun_ending_titles_with_meaningful_nouns() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v12_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "noun_titles.ko.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:05.000
처음에는 모든 RL이 수학 증명을 해보자는 식이었거든요.

00:00:06.000 --> 00:00:11.000
그래서 수학 증명은 자원이 정말 부족한 분야라고 생각했어요.

00:00:20.000 --> 00:00:25.000
마이크로소프트가 남는 CPU를 외부에 팔면서 완충 여유가 크게 줄었습니다.

00:00:26.000 --> 00:00:31.000
GitHub 다운로드 실패는 저장소 크기가 커질수록 더 자주 발생합니다.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="nounv12",
                url="https://www.youtube.com/watch?v=nounv12",
                title="명사형 제목 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt],
        )
    )

    title_lines = [line for line in document.markdown_text.splitlines() if line.startswith("### 주제 ")]
    assert title_lines
    assert all(not line.endswith(("은", "는", "이", "가", "을", "를", "거든요", "했어요", "합니다", "입니다")) for line in title_lines)
    assert all(any(noun in line for noun in ("증명", "전략", "CPU", "GitHub", "다운로드", "체계")) for line in title_lines)
