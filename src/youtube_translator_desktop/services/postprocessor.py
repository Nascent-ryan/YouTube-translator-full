from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from youtube_translator_desktop.models import SubtitleDocument


FILLER_PATTERNS = (
    r"여러분,?",
    r"저는",
    r"정말",
    r"그러니까",
    r"약간",
    r"사실",
    r"이제",
    r"확신하는[.,]?",
)


@dataclass(slots=True)
class PostProcessor:
    def process(self, document: SubtitleDocument) -> SubtitleDocument:
        cleaned_markdown = self._process_markdown(document.markdown_text)
        cleaned_plain = self._process_plain_text(document.plain_text)
        return SubtitleDocument(
            metadata=document.metadata,
            vtt_path=document.vtt_path,
            markdown_text=cleaned_markdown,
            plain_text=cleaned_plain,
            segment_count=document.segment_count,
            source_label=document.source_label,
        )

    def _process_markdown(self, markdown: str) -> str:
        lines = markdown.splitlines()
        processed: list[str] = []
        for line in lines:
            if line.startswith("- `"):
                processed.append(self._rewrite_bullet_line(line))
            elif line.startswith("  - 번역: "):
                content = line.replace("  - 번역: ", "", 1)
                processed.append(f"  - 번역: {self._to_note_style(content)}")
            elif line.startswith("## "):
                processed.append(self._rewrite_heading(line))
            else:
                processed.append(line)
        return "\n".join(processed)

    def _process_plain_text(self, plain_text: str) -> str:
        return "\n".join(self._to_note_style(line) for line in plain_text.splitlines() if line.strip())

    def _rewrite_heading(self, heading: str) -> str:
        replacements = {
            "## 한국어 전체 번역 정리": "## 한국어 번역 노트",
            "## 인상적인 원문 표현": "## 인상적이었던 원문",
            "## 전체 자막 텍스트": "## 전체 번역 텍스트",
        }
        return replacements.get(heading, heading)

    def _rewrite_bullet_line(self, line: str) -> str:
        match = re.match(r"(- `[^`]+`\s+)(.*)", line)
        if not match:
            return line
        prefix, content = match.groups()
        return f"{prefix}{self._to_note_style(content)}"

    def _to_note_style(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = self._remove_fillers(cleaned)
        cleaned = self._collapse_repetition(cleaned)
        cleaned = self._normalize_spacing(cleaned)
        cleaned = self._convert_endings(cleaned)
        cleaned = self._compress_questions(cleaned)
        return cleaned.strip()

    def _remove_fillers(self, text: str) -> str:
        result = text
        for pattern in FILLER_PATTERNS:
            result = re.sub(pattern, "", result)
        result = re.sub(r"\s+", " ", result)
        return result.strip()

    def _collapse_repetition(self, text: str) -> str:
        previous = None
        current = text
        while current != previous:
            previous = current
            current = re.sub(r"\b([가-힣A-Za-z]+)\s+\1\b", r"\1", current)
            current = re.sub(
                r"(?P<phrase>[가-힣A-Za-z0-9\s]{6,60}?)\s+(?P=phrase)",
                r"\g<phrase>",
                current,
            )
        return current

    def _normalize_spacing(self, text: str) -> str:
        text = re.sub(r"\s+([,.!?])", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text

    def _convert_endings(self, text: str) -> str:
        replacements = [
            ("했습니다.", "했음"),
            ("했습니다", "했음"),
            ("했습니다만", "했음. 다만"),
            ("낮아졌습니다.", "낮아졌음"),
            ("낮아졌습니다", "낮아졌음"),
            ("있었습니다", "있었음"),
            ("있었습니다.", "있었음"),
            ("있습니다", "있음"),
            ("있습니다.", "있음"),
            ("됩니다", "됨"),
            ("됩니다.", "됨"),
            ("보입니다", "보임"),
            ("보입니다.", "보임"),
            ("말했습니다", "말했음"),
            ("이야기했죠", "이야기했음"),
            ("이야기했습니다", "이야기했음"),
            ("필요합니다", "필요함"),
            ("중요합니다", "중요함"),
            ("중요합니다.", "중요함"),
            ("가능합니다", "가능함"),
            ("느렸죠", "느렸음"),
            ("흥미로웠습니다", "흥미로웠음"),
            ("인상적이었습니다", "인상적이었음"),
            ("인상적이었습니다.", "인상적이었음"),
            ("같습니다", "같음"),
            ("같아요", "같음"),
            ("보였죠", "보였음"),
        ]
        result = text
        for before, after in replacements:
            result = result.replace(before, after)
        if result.endswith("입니다."):
            result = result[:-4] + "임"
        elif result.endswith("입니다"):
            result = result[:-3] + "임"
        return result

    def _compress_questions(self, text: str) -> str:
        result = text
        result = re.sub(r"(.+?)공유해 주실 수 있나요\?", r"\1공유 요청", result)
        result = re.sub(r"(.+?)설명해 주시겠습니까\?", r"\1설명 요청", result)
        result = re.sub(r"(.+?)왜 그런가요\?", r"\1이유 궁금함", result)
        result = re.sub(r"공유 요청\s*[.。]*", "공유 요청. ", result)
        result = re.sub(r"\s{2,}", " ", result)
        return result
