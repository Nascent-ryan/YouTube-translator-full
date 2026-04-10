from __future__ import annotations

import re
from dataclasses import dataclass

from youtube_translator_desktop.models import SubtitleDocument

from .subtitle_downloader_v3 import DownloadResult


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
        translated_segments = self.merge_segments(
            self.parse_segments(download_result.vtt_path.read_text(encoding="utf-8"))
        )
        original_segments = self._load_original_segments(download_result)
        plain_text = "\n".join(segment.text for segment in translated_segments)
        markdown_text = self.render_markdown(download_result, translated_segments, original_segments, plain_text)

        return SubtitleDocument(
            metadata=download_result.metadata,
            vtt_path=download_result.vtt_path,
            markdown_text=markdown_text,
            plain_text=plain_text,
            segment_count=len(translated_segments),
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
            deduped_text = self._remove_overlap(previous.text, segment.text)
            if not deduped_text:
                continue

            if self._to_seconds(segment.start) - self._to_seconds(previous.start) <= self.merge_window_seconds:
                merged[-1] = VttSegment(
                    start=previous.start,
                    end=segment.end,
                    text=f"{previous.text} {deduped_text}".strip(),
                )
            else:
                merged.append(VttSegment(start=segment.start, end=segment.end, text=deduped_text))

        return merged

    def render_markdown(
        self,
        download_result: DownloadResult,
        translated_segments: list[VttSegment],
        original_segments: list[VttSegment],
        plain_text: str,
    ) -> str:
        metadata = download_result.metadata
        title = metadata.title or f"YouTube Video ({metadata.video_id})"
        bullets = "\n".join(
            self._render_bullet(segment, self._find_matching_original(segment, original_segments))
            for segment in translated_segments
        )
        notable_quotes = self._render_notable_quotes(translated_segments, original_segments)

        return f"""# {title}

## 영상 정보
- 링크: {metadata.url}
- 영상 ID: {metadata.video_id}
- 채널: {metadata.channel_name or "알 수 없음"}
- 출력 기준: 한국어 전체 번역 자막
- 사용 자막 파일: {download_result.vtt_path.name}
- 세그먼트 수: {len(translated_segments)}

## 한국어 전체 번역 정리
{bullets}

## 인상적인 원문 표현
{notable_quotes}

## 전체 자막 텍스트
{plain_text}
"""

    def _clean_text(self, text: str) -> str:
        text = TAG_PATTERN.sub("", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = re.sub(r"\s+", " ", text).strip()
        text = self._dedupe_within_line(text)
        return self._collapse_repeated_phrases(text)

    def _dedupe_within_line(self, text: str) -> str:
        words = text.split()
        if not words:
            return text

        result: list[str] = []
        for word in words:
            if result and self._normalize_word(result[-1]) == self._normalize_word(word):
                continue
            result.append(word)
            max_span = min(12, len(result) // 2)
            for span in range(max_span, 2, -1):
                left = [self._normalize_word(item) for item in result[-2 * span : -span]]
                right = [self._normalize_word(item) for item in result[-span:]]
                if left == right:
                    result = result[:-span]
                    break
        cleaned = " ".join(result)
        return self._dedupe_clauses(cleaned)

    def _remove_overlap(self, previous_text: str, current_text: str) -> str:
        if current_text in previous_text:
            return ""

        previous_words = previous_text.split()
        current_words = current_text.split()
        max_overlap = min(len(previous_words), len(current_words), 20)
        for overlap in range(max_overlap, 2, -1):
            left = [self._normalize_word(item) for item in previous_words[-overlap:]]
            right = [self._normalize_word(item) for item in current_words[:overlap]]
            if left == right:
                current_words = current_words[overlap:]
                break
        return " ".join(current_words).strip()

    def _dedupe_clauses(self, text: str) -> str:
        clauses = re.split(r"([,.!?]| 그리고 | 그런데 | 그러니까 )", text)
        if len(clauses) <= 1:
            return text

        rebuilt: list[str] = []
        previous_normalized = ""
        for clause in clauses:
            normalized = re.sub(r"[\W_]+", "", clause).lower()
            if normalized and normalized == previous_normalized:
                continue
            rebuilt.append(clause)
            if normalized:
                previous_normalized = normalized

        return "".join(rebuilt).strip()

    def _collapse_repeated_phrases(self, text: str) -> str:
        previous = None
        current = text
        while current != previous:
            previous = current
            current = re.sub(r"\b([^\W\d_]+)\s+\1\b", r"\1", current, flags=re.IGNORECASE)
            current = re.sub(
                r"(?P<phrase>(?:[^\W\d_]+(?:\s+[^\W\d_]+){1,7}))\s+(?P=phrase)",
                r"\g<phrase>",
                current,
                flags=re.IGNORECASE,
            )
            current = re.sub(
                r"(?P<phrase>[^,.!?]{8,80})[,.!?\s]+(?P=phrase)",
                r"\g<phrase>",
                current,
                flags=re.IGNORECASE,
            )
        return current.strip()

    def _load_original_segments(self, download_result: DownloadResult) -> list[VttSegment]:
        for path in download_result.related_vtt_paths:
            if path == download_result.vtt_path:
                continue
            if ".en." in path.name or ".en-" in path.name or path.name.endswith(".en.vtt"):
                return self.merge_segments(self.parse_segments(path.read_text(encoding="utf-8")))
        return []

    def _find_matching_original(
        self,
        translated_segment: VttSegment,
        original_segments: list[VttSegment],
    ) -> VttSegment | None:
        target_seconds = self._to_seconds(translated_segment.start)
        for original_segment in original_segments:
            if abs(self._to_seconds(original_segment.start) - target_seconds) <= 8:
                return original_segment
        return None

    def _render_bullet(self, segment: VttSegment, original_segment: VttSegment | None) -> str:
        line = f"- `{segment.start}` {segment.text}"
        if original_segment and self._should_include_original(original_segment.text):
            line += f'\n  원문: "{original_segment.text}"'
        return line

    def _render_notable_quotes(
        self,
        translated_segments: list[VttSegment],
        original_segments: list[VttSegment],
    ) -> str:
        lines: list[str] = []
        for segment in translated_segments:
            original_segment = self._find_matching_original(segment, original_segments)
            if not original_segment or not self._should_include_original(original_segment.text):
                continue
            lines.append(
                f'- `{segment.start}` "{original_segment.text}"\n  - 번역: {segment.text}'
            )
            if len(lines) >= 8:
                break
        return "\n".join(lines) if lines else "- 별도 병기할 원문 표현 없음"

    def _should_include_original(self, text: str) -> bool:
        return len(text) >= 40

    def _normalize_word(self, word: str) -> str:
        return re.sub(r"[\W_]+", "", word).lower()

    def _to_seconds(self, timestamp: str) -> float:
        hours, minutes, rest = timestamp.split(":")
        seconds, milliseconds = rest.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
