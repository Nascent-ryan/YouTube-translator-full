from __future__ import annotations

from dataclasses import dataclass

from .subtitle_downloader_v3 import DownloadResult
from .vtt_converter_v11 import VttConverter


@dataclass(slots=True)
class OriginalMarkdownBuilder:
    def build(self, download_result: DownloadResult, converter: VttConverter) -> str | None:
        english_vtt = self._find_english_vtt(download_result)
        if english_vtt is None:
            return None

        segments = converter.merge_segments(
            converter.parse_segments(english_vtt.read_text(encoding="utf-8"))
        )
        if not segments:
            return None

        paragraphs = self._group_paragraphs([segment.text for segment in segments])
        metadata = download_result.metadata
        title = metadata.title or f"YouTube Video ({metadata.video_id})"

        body = "\n\n".join(paragraphs)
        return f"""# {title} (English Original)

## Video Info
- Link: {metadata.url}
- Video ID: {metadata.video_id}
- Channel: {metadata.channel_name or "Unknown"}
- Subtitle File: {english_vtt.name}

## English Transcript
{body}
"""

    def _find_english_vtt(self, download_result: DownloadResult):
        for path in download_result.related_vtt_paths:
            if ".en." in path.name or ".en-" in path.name or path.name.endswith(".en.vtt"):
                return path
        return None

    def _group_paragraphs(self, texts: list[str]) -> list[str]:
        paragraphs: list[str] = []
        current: list[str] = []
        for text in texts:
            current.append(text)
            if len(current) >= 3:
                paragraphs.append(" ".join(current).strip())
                current = []
        if current:
            paragraphs.append(" ".join(current).strip())
        return paragraphs
