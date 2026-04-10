from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.error import URLError
from urllib.request import urlopen

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

from youtube_translator_desktop.models import TranscriptDocument, VideoMetadata

from .errors import TranscriptError
from .url_utils import extract_video_id


@dataclass(slots=True)
class TranscriptFetcher:
    minimum_characters: int = 200

    def fetch(self, url: str) -> TranscriptDocument:
        video_id = extract_video_id(url)
        api = YouTubeTranscriptApi()

        try:
            transcript_list = api.list(video_id)
        except (NoTranscriptFound, TranscriptsDisabled) as exc:
            raise TranscriptError("이 영상에서는 사용 가능한 자막을 찾지 못했습니다.") from exc
        except requests.exceptions.ProxyError as exc:
            raise TranscriptError(
                "YouTube 연결에 실패했습니다. 시스템 프록시 설정이 잘못되었거나 차단된 것 같습니다."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise TranscriptError("YouTube에 연결하지 못했습니다. 네트워크 상태를 확인해 주세요.") from exc
        except Exception as exc:
            raise TranscriptError(f"자막 목록을 불러오지 못했습니다: {exc}") from exc

        transcript = self._select_transcript(transcript_list)
        try:
            segments = transcript.fetch()
        except Exception as exc:
            raise TranscriptError(f"자막 내용을 불러오지 못했습니다: {exc}") from exc

        transcript_text = "\n".join(
            segment.text.replace("\n", " ").strip() for segment in segments if segment.text.strip()
        ).strip()

        if len(transcript_text) < self.minimum_characters:
            raise TranscriptError(
                "자막 길이가 너무 짧아 안정적인 정리를 만들기 어렵습니다. 다른 영상을 시도해 주세요."
            )

        metadata = VideoMetadata(
            video_id=video_id,
            url=url.strip(),
            title=f"YouTube Video ({video_id})",
            channel_name=None,
            language_code=getattr(transcript, "language_code", None),
        )
        self._enrich_metadata(metadata)

        return TranscriptDocument(
            metadata=metadata,
            transcript_text=transcript_text,
            segment_count=len(segments),
            source_label="youtube_transcript",
        )

    @staticmethod
    def _select_transcript(transcript_list):
        manual = []
        generated = []
        for transcript in transcript_list:
            if getattr(transcript, "is_generated", False):
                generated.append(transcript)
            else:
                manual.append(transcript)

        preferred_languages = ("ko", "en")
        for pool in (manual, generated):
            for lang in preferred_languages:
                for transcript in pool:
                    if getattr(transcript, "language_code", "") == lang:
                        return transcript
            if pool:
                return pool[0]

        raise TranscriptError("사용 가능한 자막을 찾지 못했습니다.")

    @staticmethod
    def _enrich_metadata(metadata: VideoMetadata) -> None:
        oembed_url = f"https://www.youtube.com/oembed?url={metadata.url}&format=json"
        try:
            with urlopen(oembed_url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError):
            return

        metadata.title = payload.get("title") or metadata.title
        metadata.channel_name = payload.get("author_name") or metadata.channel_name
