from __future__ import annotations

import re
from dataclasses import dataclass

from youtube_translator_desktop.models import SubtitleDocument

from .subtitle_downloader_v3 import DownloadResult


TIMESTAMP_PATTERN = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")
NUMBER_PATTERN = re.compile(r"\d")

QUESTION_HINTS_KO = ("왜", "어떻게", "무엇", "얼마나", "가능한가", "있나요", "보시나요", "설명", "공유")
QUESTION_HINTS_EN = ("why", "how", "what", "can you", "do you", "are there", "could you", "would you")
INSIGHT_HINTS = (
    "cpu",
    "gpu",
    "bottleneck",
    "hyper scaler",
    "neo cloud",
    "agent",
    "reinforcement learning",
    "inference",
    "capacity",
    "cluster",
    "deploy",
)
STOPWORDS = {
    "그리고",
    "그래서",
    "하지만",
    "그런데",
    "이제",
    "정말",
    "그냥",
    "대한",
    "있음",
    "하는",
    "했다",
    "했다고",
    "이야기",
    "설명",
    "부분",
    "내용",
}


@dataclass(slots=True)
class VttSegment:
    start: str
    end: str
    text: str


@dataclass(slots=True)
class DialogueTurn:
    speaker: str
    text: str
    original_text: str | None = None


@dataclass(slots=True)
class TopicBlock:
    title: str
    turns: list[DialogueTurn]


@dataclass(slots=True)
class VttConverter:
    merge_window_seconds: int = 16

    def convert(self, download_result: DownloadResult) -> SubtitleDocument:
        translated_segments = self.merge_segments(
            self.parse_segments(download_result.vtt_path.read_text(encoding="utf-8"))
        )
        original_segments = self._load_original_segments(download_result)
        turns = self._build_turns(translated_segments, original_segments)
        topic_blocks = self._group_topics(turns)
        plain_text = "\n".join(turn.text for turn in turns)
        markdown_text = self.render_markdown(download_result, topic_blocks, plain_text)

        return SubtitleDocument(
            metadata=download_result.metadata,
            vtt_path=download_result.vtt_path,
            markdown_text=markdown_text,
            plain_text=plain_text,
            segment_count=len(turns),
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
            current_text = self._remove_overlap(previous.text, segment.text)
            if not current_text:
                continue

            if self._to_seconds(segment.start) - self._to_seconds(previous.start) <= self.merge_window_seconds:
                merged[-1] = VttSegment(
                    start=previous.start,
                    end=segment.end,
                    text=f"{previous.text} {current_text}".strip(),
                )
            else:
                merged.append(VttSegment(start=segment.start, end=segment.end, text=current_text))
        return merged

    def render_markdown(
        self,
        download_result: DownloadResult,
        topic_blocks: list[TopicBlock],
        plain_text: str,
    ) -> str:
        metadata = download_result.metadata
        title = metadata.title or f"YouTube Video ({metadata.video_id})"
        topic_sections = "\n\n".join(self._render_topic_block(block, index + 1) for index, block in enumerate(topic_blocks))
        notable_quotes = self._render_notable_quotes(topic_blocks)

        return f"""# {title}

## 영상 정보
- 링크: {metadata.url}
- 영상 ID: {metadata.video_id}
- 채널: {metadata.channel_name or "알 수 없음"}
- 출력 기준: 한국어 번역 정리
- 사용 자막 파일: {download_result.vtt_path.name}
- 발화 수: {sum(len(block.turns) for block in topic_blocks)}

## 대화 정리
{topic_sections}

## 인상적인 원문
{notable_quotes}

## 전체 번역 텍스트
{plain_text}
"""

    def _render_topic_block(self, block: TopicBlock, index: int) -> str:
        lines = [f"### 주제 {index}. {block.title}"]
        current_speaker = None
        for turn in block.turns:
            if turn.speaker != current_speaker:
                lines.append(f"**{turn.speaker}**")
                current_speaker = turn.speaker
            bullet = f"- {turn.text}"
            if turn.original_text and self._should_include_original(turn.text, turn.original_text):
                bullet += f'\n  원문: "{turn.original_text}"'
            lines.append(bullet)
        return "\n".join(lines)

    def _render_notable_quotes(self, topic_blocks: list[TopicBlock]) -> str:
        lines: list[str] = []
        for block in topic_blocks:
            for turn in block.turns:
                if turn.original_text and self._should_include_original(turn.text, turn.original_text):
                    lines.append(f'- "{turn.original_text}"\n  - 번역: {turn.text}')
                if len(lines) >= 4:
                    return "\n".join(lines)
        return "- 별도 병기할 원문 표현 없음"

    def _build_turns(
        self,
        translated_segments: list[VttSegment],
        original_segments: list[VttSegment],
    ) -> list[DialogueTurn]:
        turns: list[DialogueTurn] = []
        current_speaker = "게스트"

        for segment in translated_segments:
            original = self._find_matching_original(segment, original_segments)
            if self._is_question(segment.text, original.text if original else ""):
                current_speaker = "진행자"
            elif turns and turns[-1].speaker == "진행자":
                current_speaker = "게스트"

            turns.append(
                DialogueTurn(
                    speaker=current_speaker,
                    text=segment.text,
                    original_text=original.text if original else None,
                )
            )
        return turns

    def _group_topics(self, turns: list[DialogueTurn]) -> list[TopicBlock]:
        if not turns:
            return []

        blocks: list[TopicBlock] = []
        current_turns: list[DialogueTurn] = [turns[0]]
        current_keywords = self._keywords(turns[0].text)

        for turn in turns[1:]:
            turn_keywords = self._keywords(turn.text)
            similarity = self._similarity(current_keywords, turn_keywords)
            speaker_changed = turn.speaker != current_turns[-1].speaker
            should_split = similarity < 0.18 and len(current_turns) >= 3 and speaker_changed

            if should_split:
                blocks.append(TopicBlock(title=self._make_topic_title(current_turns), turns=current_turns))
                current_turns = [turn]
                current_keywords = turn_keywords
            else:
                current_turns.append(turn)
                current_keywords |= turn_keywords

        blocks.append(TopicBlock(title=self._make_topic_title(current_turns), turns=current_turns))
        return blocks

    def _make_topic_title(self, turns: list[DialogueTurn]) -> str:
        keywords = self._keywords(" ".join(turn.text for turn in turns))
        ordered = sorted(keywords, key=lambda item: (-len(item), item))
        if not ordered:
            return "주요 논의"
        if len(ordered) == 1:
            return ordered[0]
        return " / ".join(ordered[:2])

    def _keywords(self, text: str) -> set[str]:
        words = re.findall(r"[가-힣A-Za-z0-9-]{3,}", text.lower())
        return {word for word in words if word not in STOPWORDS}

    def _similarity(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        intersection = len(left & right)
        union = len(left | right)
        return intersection / union if union else 0.0

    def _load_original_segments(self, download_result: DownloadResult) -> list[VttSegment]:
        for path in download_result.related_vtt_paths:
            if path == download_result.vtt_path:
                continue
            if ".en." in path.name or ".en-" in path.name or path.name.endswith(".en.vtt"):
                return self.merge_segments(self.parse_segments(path.read_text(encoding="utf-8")))
        return []

    def _find_matching_original(self, translated_segment: VttSegment, original_segments: list[VttSegment]) -> VttSegment | None:
        target = self._to_seconds(translated_segment.start)
        for original in original_segments:
            if abs(self._to_seconds(original.start) - target) <= 8:
                return original
        return None

    def _is_question(self, translated_text: str, original_text: str) -> bool:
        lower_ko = translated_text.lower()
        lower_en = original_text.lower()
        if "?" in translated_text or "?" in original_text:
            return True
        if any(token in lower_ko for token in QUESTION_HINTS_KO):
            return True
        return any(token in lower_en for token in QUESTION_HINTS_EN)

    def _should_include_original(self, translated_text: str, original_text: str) -> bool:
        lower_original = original_text.lower()
        if NUMBER_PATTERN.search(original_text):
            return True
        if any(token in lower_original for token in INSIGHT_HINTS):
            return True
        if len(original_text) >= 120 and len(translated_text) >= 70:
            return True
        return False

    def _clean_text(self, text: str) -> str:
        text = TAG_PATTERN.sub("", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = re.sub(r"\s+", " ", text).strip()
        text = self._dedupe_within_line(text)
        return self._collapse_repeated_phrases(text)

    def _dedupe_within_line(self, text: str) -> str:
        words = text.split()
        result: list[str] = []
        for word in words:
            if result and self._normalize_word(result[-1]) == self._normalize_word(word):
                continue
            result.append(word)
            max_span = min(10, len(result) // 2)
            for span in range(max_span, 2, -1):
                left = [self._normalize_word(item) for item in result[-2 * span : -span]]
                right = [self._normalize_word(item) for item in result[-span:]]
                if left == right:
                    result = result[:-span]
                    break
        return " ".join(result)

    def _collapse_repeated_phrases(self, text: str) -> str:
        previous = None
        current = text
        while current != previous:
            previous = current
            current = re.sub(r"\b([가-힣A-Za-z]+)\s+\1\b", r"\1", current)
            current = re.sub(
                r"(?P<phrase>[가-힣A-Za-z0-9\s]{8,80}?)\s+(?P=phrase)",
                r"\g<phrase>",
                current,
            )
        return current.strip()

    def _remove_overlap(self, previous_text: str, current_text: str) -> str:
        if current_text in previous_text:
            return ""
        previous_words = previous_text.split()
        current_words = current_text.split()
        max_overlap = min(len(previous_words), len(current_words), 16)
        for overlap in range(max_overlap, 2, -1):
            left = [self._normalize_word(item) for item in previous_words[-overlap:]]
            right = [self._normalize_word(item) for item in current_words[:overlap]]
            if left == right:
                current_words = current_words[overlap:]
                break
        return " ".join(current_words).strip()

    def _normalize_word(self, word: str) -> str:
        return re.sub(r"[\W_]+", "", word).lower()

    def _to_seconds(self, timestamp: str) -> float:
        hours, minutes, rest = timestamp.split(":")
        seconds, milliseconds = rest.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
