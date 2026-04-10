from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v13 import VttConverter


def test_vtt_converter_v13_uses_core_nouns_for_titles() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v13_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "core_titles.ko.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:05.000
최근 GitHub 다운로드 실패가 자주 보였습니다.

00:00:06.000 --> 00:00:11.000
저희도 계속 추적하고 있는데 실제로 실패 빈도가 꽤 올라갔습니다.

00:00:20.000 --> 00:00:25.000
마이크로소프트가 남는 CPU를 외부에 팔면서 완충 여유가 크게 줄었습니다.

00:00:26.000 --> 00:00:31.000
CPU 수요는 에이전트 워크로드 때문에 빠르게 늘고 있습니다.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="corev13",
                url="https://www.youtube.com/watch?v=corev13",
                title="핵심 명사 제목 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt],
        )
    )

    title_lines = [line for line in document.markdown_text.splitlines() if line.startswith("### 주제 ")]
    assert title_lines
    assert all(not line.endswith(("은", "는", "이", "가", "을", "를", "합니다", "입니다")) for line in title_lines)
    assert all(any(noun in line for noun in ("GitHub", "다운로드", "마이크로소프트", "CPU", "에이전트")) for line in title_lines)
