from __future__ import annotations

import re
from dataclasses import dataclass

from youtube_translator_desktop.models import SubtitleDocument

from .subtitle_downloader_v2 import DownloadResult


TIMESTAMP_PATTERN = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class VttSegment:
    start: str
    end: str
    text: str


@dataclass(slots=True)
class VttConverter:
    merge_window_seconds: int = 18

    def convert(self, download_result: DownloadResult) -> SubtitleDocument:
        raw_text = download_result.vtt_path.read_text(encoding="utf-8")
        segments = self.parse_segments(raw_text)
        merged_segments = self.merge_segments(segments)
        plain_text = "\n".join(segment.text for segment in merged_segments)
        markdown_text = self.render_markdown(download_result, merged_segments, plain_text)

        return SubtitleDocument(
            metadata=download_result.metadata,
            vtt_path=download_result.vtt_path,
            markdown_text=markdown_text,
            plain_text=plain_text,
            segment_count=len(merged_segments),
        )

    def parse_segments(self, raw_text: str) -> list[VttSegment]:
        lines = [line.rstrip("\ufeff") for line in raw_text.splitlines()]
        segments: list[VttSegment] = []
        current_timestamp: tuple[str, str] | None = None
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped == "WEBVTT":
                if current_timestamp and current_lines:
                    segments.append(
                        VttSegment(
                            start=current_timestamp[0],
                            end=current_timestamp[1],
                            text=self._clean_text(" ".join(current_lines)),
                        )
                    )
                current_timestamp = None
                current_lines = []
                continue

            timestamp_match = TIMESTAMP_PATTERN.match(stripped)
            if timestamp_match:
                if current_timestamp and current_lines:
                    segments.append(
                        VttSegment(
                            start=current_timestamp[0],
                            end=current_timestamp[1],
                            text=self._clean_text(" ".join(current_lines)),
                        )
                    )
                current_timestamp = (timestamp_match.group("start"), timestamp_match.group("end"))
                current_lines = []
                continue

            if current_timestamp and not stripped.isdigit():
                current_lines.append(stripped)

        if current_timestamp and current_lines:
            segments.append(
                VttSegment(
                    start=current_timestamp[0],
                    end=current_timestamp[1],
                    text=self._clean_text(" ".join(current_lines)),
                )
            )

        return [segment for segment in segments if segment.text]

    def merge_segments(self, segments: list[VttSegment]) -> list[VttSegment]:
        if not segments:
            return []

        merged: list[VttSegment] = [segments[0]]
        for segment in segments[1:]:
            previous = merged[-1]
            if (
                self._to_seconds(segment.start) - self._to_seconds(previous.start) <= self.merge_window_seconds
                and segment.text != previous.text
            ):
                merged[-1] = VttSegment(
                    start=previous.start,
                    end=segment.end,
                    text=f"{previous.text} {segment.text}".strip(),
                )
            else:
                merged.append(segment)

        return merged

    def render_markdown(
        self,
        download_result: DownloadResult,
        segments: list[VttSegment],
        plain_text: str,
    ) -> str:
        metadata = download_result.metadata
        segment_lines = "\n".join(f"- `{segment.start}` {segment.text}" for segment in segments)

        return f"""# {metadata.title}

## 영상 정보
- 링크: {metadata.url}
- 영상 ID: {metadata.video_id}
- 채널: {metadata.channel_name or "알 수 없음"}
- 자막 언어: {metadata.language_code or "알 수 없음"}
- 자막 파일: {download_result.vtt_path.name}
- 세그먼트 수: {len(segments)}

## Claude 업로드용 메모
아래 자막 정리본을 기준으로 한국어 요약, 핵심 포인트, 인상적인 원문 표현을 정리해 주세요.

## 자막 정리본
{segment_lines}

## 전체 자막 텍스트
{plain_text}
"""

    def _clean_text(self, text: str) -> str:
        text = TAG_PATTERN.sub("", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _to_seconds(self, timestamp: str) -> float:
        hours, minutes, rest = timestamp.split(":")
        seconds, milliseconds = rest.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
