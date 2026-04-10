from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v4 import VttConverter


def test_vtt_converter_v4_uses_clean_speaker_labels() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v4_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "sample.ko.vtt"
    en_vtt = tmp_path / "sample.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:02.000
왜 네오클라우드가 중요한가요?

00:00:03.000 --> 00:00:05.000
GPU와 CPU 병목이 이전과 다르게 나타납니다.

00:00:30.000 --> 00:00:33.000
강화학습 워크로드가 CPU 수요를 키웁니다.
""",
        encoding="utf-8",
    )
    en_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:02.000
Why do neo clouds matter?

00:00:03.000 --> 00:00:05.000
GPU and CPU bottlenecks have changed.

00:00:30.000 --> 00:00:33.000
RL workloads increase CPU demand.
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
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt, en_vtt],
        )
    )

    assert "### 주제 1." in document.markdown_text
    assert "**진행자**" in document.markdown_text
    assert "**게스트**" in document.markdown_text
    assert "00:00" not in document.markdown_text


def test_vtt_converter_v4_limits_original_quotes_to_one_global_entry() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v4_quotes_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "quotes.ko.vtt"
    en_vtt = tmp_path / "quotes.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
하이퍼스케일러보다 네오클라우드가 빠르게 움직인다는 설명입니다.

00:00:05.000 --> 00:00:10.000
2026년에는 CPU와 GPU 병목이 동시에 커질 수 있다는 설명입니다.

00:00:20.000 --> 00:00:25.000
에이전트 워크로드는 추론 클러스터 배포 방식을 다시 설계하게 만든다는 이야기입니다.
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
                video_id="quotecheck1",
                url="https://www.youtube.com/watch?v=quotecheck1",
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
