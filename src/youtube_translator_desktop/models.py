from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class VideoMetadata:
    video_id: str
    url: str
    title: str
    channel_name: str | None = None
    language_code: str | None = None


@dataclass(slots=True)
class SubtitleDocument:
    metadata: VideoMetadata
    vtt_path: Path
    markdown_text: str
    plain_text: str
    segment_count: int
    source_label: str = "yt-dlp"


@dataclass(slots=True)
class GenerationResult:
    subtitle_document: SubtitleDocument
    output_path: Path
    markdown_text: str
    original_output_path: Path | None = None
    original_markdown_text: str | None = None
    warnings: list[str] = field(default_factory=list)
