from pathlib import Path
from uuid import uuid4

from youtube_translator_desktop.models import VideoMetadata
from youtube_translator_desktop.services.openai_translator import OpenAITranslator
from youtube_translator_desktop.services.subtitle_downloader_v3 import DownloadResult


def test_openai_translator_is_disabled_without_key() -> None:
    translator = OpenAITranslator(api_key=None)

    assert not translator.is_enabled()


def test_openai_translator_finds_english_vtt() -> None:
    work_dir = Path(".pytest_tmp") / f"openai_translator_{uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=True)
    english_path = work_dir / "sample.en.vtt"
    korean_path = work_dir / "sample.ko.vtt"
    english_path.write_text("WEBVTT\n", encoding="utf-8")
    korean_path.write_text("WEBVTT\n", encoding="utf-8")
    download_result = DownloadResult(
        metadata=VideoMetadata(video_id="sample", url="https://youtu.be/sample", title="Sample"),
        vtt_path=korean_path,
        related_vtt_paths=[korean_path, english_path],
    )

    translator = OpenAITranslator(api_key="test")

    assert translator._find_english_vtt(download_result) == english_path


def test_openai_translator_batches_by_character_count() -> None:
    translator = OpenAITranslator(api_key="test", max_batch_chars=10)

    batches = translator._batches(["12345", "67890", "abc"])

    assert batches == [(0, ["12345", "67890"]), (2, ["abc"])]
