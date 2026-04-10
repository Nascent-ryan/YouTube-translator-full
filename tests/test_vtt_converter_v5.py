from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v5 import VttConverter


def test_vtt_converter_v5_uses_natural_topic_titles() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v5_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "sample.ko.vtt"
    en_vtt = tmp_path / "sample.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
최근 GitHub를 계속 확인하고 있는데 다운로드 실패가 꽤 자주 보입니다.

00:00:05.000 --> 00:00:08.000
마이크로소프트는 남는 CPU를 외부 회사에 팔아버렸기 때문에 상황이 더 불안정합니다.

00:00:20.000 --> 00:00:24.000
CPU 수요가 다시 늘면서 클러스터 운영도 점점 더 빡빡해지고 있습니다.
""",
        encoding="utf-8",
    )
    en_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
GitHub downloads are failing more often lately.

00:00:05.000 --> 00:00:08.000
Microsoft sold spare CPU capacity to outside companies, so the situation is unstable.

00:00:20.000 --> 00:00:24.000
CPU demand is climbing again and cluster operations are getting tighter.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="topicv5test",
                url="https://www.youtube.com/watch?v=topicv5test",
                title="주제 제목 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt, en_vtt],
        )
    )

    title_line = next(line for line in document.markdown_text.splitlines() if line.startswith("### 주제 1."))
    assert title_line == "### 주제 1. GitHub 안정성과 마이크로소프트 전략"


def test_vtt_converter_v5_keeps_single_original_quote_limit() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v5_quotes_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "quotes.ko.vtt"
    en_vtt = tmp_path / "quotes.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
하이퍼스케일러보다 네오클라우드가 더 빠르게 움직이고 있습니다.

00:00:05.000 --> 00:00:10.000
2026년에는 CPU와 GPU 병목이 동시에 더 심해질 수 있습니다.

00:00:20.000 --> 00:00:25.000
에이전트 워크로드는 추론 클러스터 배포 방식을 다시 설계하게 만듭니다.
""",
        encoding="utf-8",
    )
    en_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
Neo clouds are moving faster than hyperscalers.

00:00:05.000 --> 00:00:10.000
In 2026, CPU and GPU bottlenecks get worse at the same time.

00:00:20.000 --> 00:00:25.000
Agent workloads force teams to redesign how they deploy inference clusters.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="quotecheck5",
                url="https://www.youtube.com/watch?v=quotecheck5",
                title="원문 병기 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt, en_vtt],
        )
    )

    assert "원문:" not in document.markdown_text
    assert document.markdown_text.count('\n- "') <= 1
