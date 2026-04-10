from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v3 import VttConverter


def test_vtt_converter_groups_topics_and_removes_timestamps() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v3_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "sample.ko.vtt"
    en_vtt = tmp_path / "sample.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:02.000
왜 네오 클라우드가 중요한가요?

00:00:03.000 --> 00:00:05.000
GPU와 CPU 병목이 달라졌습니다.

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
    assert "`00:00" not in document.markdown_text
