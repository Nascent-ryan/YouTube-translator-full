from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult
from youtube_translator_desktop.services.vtt_converter_v11 import VttConverter


def test_vtt_converter_v10_filters_awkward_sentence_like_titles() -> None:
    tmp_path = Path(".pytest_local") / f"vtt_v10_{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    ko_vtt = tmp_path / "awkward.ko.vtt"
    ko_vtt.write_text(
        """WEBVTT

00:00:00.000 --> 00:00:05.000
처음에는 모든 RL이 수학 증명을 해보자는 식이었거든요.

00:00:06.000 --> 00:00:11.000
그래서 수학 증명은 자원이 정말 부족한 분야라고 생각했어요.

00:00:20.000 --> 00:00:25.000
TSMC에는 3나노미터 공정 설비가 부족해서 다른 곳에서 칩을 만들어야 합니다.

00:00:26.000 --> 00:00:31.000
모든 AI 칩이 3나노미터로 이동하는 흐름도 같은 맥락입니다.
""",
        encoding="utf-8",
    )

    converter = VttConverter(merge_window_seconds=2)
    document = converter.convert(
        DownloadResult(
            metadata=VideoMetadata(
                video_id="awkwardv10",
                url="https://www.youtube.com/watch?v=awkwardv10",
                title="어색한 제목 방지 테스트",
                channel_name="Sample Channel",
                language_code="ko",
            ),
            vtt_path=ko_vtt,
            related_vtt_paths=[ko_vtt],
        )
    )

    title_lines = [line for line in document.markdown_text.splitlines() if line.startswith("### 주제 ")]
    assert title_lines
    assert all("생각했어요" not in line for line in title_lines)
    assert all("식이었거든요" not in line for line in title_lines)
    assert all("마찬가지입니다" not in line for line in title_lines)
