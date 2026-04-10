from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v7 import VttConverter


def test_vtt_converter_v7_renders_question_and_answer_labels() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v7_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "qa.ko.vtt"
    en_vtt = tmp_path / "qa.en.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
최근 GitHub 다운로드 실패가 자주 보였는지 궁금합니다.

00:00:05.000 --> 00:00:11.000
저희도 계속 추적하고 있는데 실제로 실패 빈도가 꽤 올라갔습니다.

00:00:12.000 --> 00:00:18.000
마이크로소프트가 남는 CPU를 외부에 팔면서 완충 여유가 크게 줄었습니다.

00:00:19.000 --> 00:00:23.000
그럼 CPU 수요는 왜 이렇게 빨리 늘었나요?

00:00:24.000 --> 00:00:31.000
에이전트 워크로드와 강화학습 루프가 길어지면서 CPU 요청이 급격히 늘어났습니다.
""",
        encoding="utf-8",
    )
    en_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:04.000
Have you noticed GitHub download failures becoming more frequent lately?

00:00:05.000 --> 00:00:11.000
We have been tracking it and the failure rate has gone up quite a bit.

00:00:12.000 --> 00:00:18.000
Microsoft sold spare CPU capacity to outside companies, so the buffer has shrunk.

00:00:19.000 --> 00:00:23.000
So why is CPU demand rising this quickly?

00:00:24.000 --> 00:00:31.000
Agent workloads and longer RL loops have sharply increased CPU requests.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="qav7test",
                url="https://www.youtube.com/watch?v=qav7test",
                title="Q A 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt, en_vtt],
        )
    )

    assert "**Q**" in document.markdown_text
    assert "**A**" in document.markdown_text
    assert "**진행자**" not in document.markdown_text
    assert "**게스트**" not in document.markdown_text
    assert "### 주제 1." in document.markdown_text
    assert "### 주제 2." in document.markdown_text
