import pytest

from youtube_translator_desktop.services.errors import ValidationError
from youtube_translator_desktop.services.url_utils import extract_video_id


def test_extract_video_id_from_watch_url() -> None:
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_short_url() -> None:
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        extract_video_id("https://example.com/watch?v=dQw4w9WgXcQ")
