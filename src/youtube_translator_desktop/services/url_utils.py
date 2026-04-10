from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from .errors import ValidationError


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    normalized_url = url.strip()
    if not normalized_url:
        raise ValidationError("YouTube 링크를 입력해 주세요.")

    parsed = urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("YouTube 링크는 http 또는 https 형식이어야 합니다.")
    if parsed.netloc.lower() not in YOUTUBE_HOSTS:
        raise ValidationError("유효한 YouTube 링크만 지원합니다.")

    if parsed.netloc.lower() == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith("/shorts/"):
        candidate = parsed.path.split("/")[2]
    elif parsed.path.startswith("/embed/"):
        candidate = parsed.path.split("/")[2]
    else:
        raise ValidationError("현재는 일반 YouTube 영상 링크만 지원합니다.")

    if not VIDEO_ID_PATTERN.match(candidate):
        raise ValidationError("YouTube 영상 ID를 확인할 수 없습니다.")

    return candidate
