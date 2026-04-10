from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v9 import VttConverter


def test_vtt_converter_v9_avoids_repeating_same_topic_title() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v9_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "titles.ko.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:05.000
최근 GitHub 다운로드 실패가 자주 보였습니다.

00:00:06.000 --> 00:00:11.000
저희도 계속 추적하고 있는데 실제로 실패 빈도가 꽤 올라갔습니다.

00:00:12.000 --> 00:00:17.000
마이크로소프트가 남는 CPU를 외부에 팔면서 완충 여유가 크게 줄었습니다.

00:00:30.000 --> 00:00:35.000
CPU 수요는 에이전트 워크로드 때문에 빠르게 늘고 있습니다.

00:00:36.000 --> 00:00:41.000
추론 클러스터 운영도 그만큼 더 빡빡해지고 있습니다.

00:00:55.000 --> 00:01:00.000
GitHub 아카이브 다운로드 실패는 특히 대용량 저장소에서 더 자주 발생합니다.

00:01:01.000 --> 00:01:06.000
실패 유형을 보면 네트워크보다 내부 배포 체계 영향이 더 커 보입니다.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="topicv9test",
                url="https://www.youtube.com/watch?v=topicv9test",
                title="주제 제목 정제 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt],
        )
    )

    title_lines = [line for line in document.markdown_text.splitlines() if line.startswith("### 주제 ")]
    assert len(title_lines) >= 2
    assert len(title_lines) == len(set(title_lines))
    assert all("주요 논의" not in line for line in title_lines)
