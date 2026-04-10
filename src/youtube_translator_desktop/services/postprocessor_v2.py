from __future__ import annotations

import re
from dataclasses import dataclass

from youtube_translator_desktop.models import SubtitleDocument


FILLERS = (
    "여러분",
    "정말",
    "사실",
    "약간",
    "그러니까",
    "뭐랄까",
    "확신하는",
)


@dataclass(slots=True)
class PostProcessor:
    def process(self, document: SubtitleDocument) -> SubtitleDocument:
        markdown = self._clean_markdown(document.markdown_text)
        plain_text = self._clean_plain_text(document.plain_text)
        return SubtitleDocument(
            metadata=document.metadata,
            vtt_path=document.vtt_path,
            markdown_text=markdown,
            plain_text=plain_text,
            segment_count=document.segment_count,
            source_label=document.source_label,
        )

    def _clean_markdown(self, markdown: str) -> str:
        lines = markdown.splitlines()
        output: list[str] = []
        for line in lines:
            if line.startswith("## "):
                output.append(self._rewrite_heading(line))
            elif line.startswith("- "):
                output.append(self._clean_bullet(line))
            elif line.startswith("  - 번역: "):
                content = line.replace("  - 번역: ", "", 1)
                output.append(f"  - 번역: {self._to_note_style(content)}")
            else:
                output.append(line)
        return "\n".join(output)

    def _rewrite_heading(self, line: str) -> str:
        replacements = {
            "## 대화 정리": "## 주제별 대화 정리",
            "## 인상적인 원문": "## 선택 원문",
            "## 전체 번역 텍스트": "## 전체 번역문",
        }
        return replacements.get(line, line)

    def _clean_plain_text(self, plain_text: str) -> str:
        return "\n".join(self._to_note_style(line) for line in plain_text.splitlines() if line.strip())

    def _clean_bullet(self, line: str) -> str:
        if line.startswith("- 링크:") or line.startswith("- 영상 ID:") or line.startswith("- 채널:") or line.startswith("- 출력 기준:") or line.startswith("- 사용 자막 파일:") or line.startswith("- 발화 수:"):
            return line
        if line.startswith("- \""):
            return line
        return "- " + self._to_note_style(line[2:])

    def _to_note_style(self, text: str) -> str:
        value = text.strip()
        for filler in FILLERS:
            value = value.replace(filler, "")
        value = re.sub(r"\s{2,}", " ", value)
        value = value.replace("했습니다", "했음")
        value = value.replace("했습니다.", "했음")
        value = value.replace("있습니다", "있음")
        value = value.replace("있습니다.", "있음")
        value = value.replace("보입니다", "보임")
        value = value.replace("보입니다.", "보임")
        value = value.replace("같습니다", "같음")
        value = value.replace("같습니다.", "같음")
        value = value.replace("중요합니다", "중요함")
        value = value.replace("중요합니다.", "중요함")
        value = value.replace("인상적이었습니다", "인상적이었음")
        value = value.replace("인상적이었습니다.", "인상적이었음")
        value = value.replace("흥미로웠습니다", "흥미로웠음")
        value = value.replace("흥미로웠습니다.", "흥미로웠음")
        value = re.sub(r"공유 요청[. ,]*", "공유 요청. ", value)
        value = value.replace(".,.,", ". ")
        value = value.replace(".,.", ". ")
        value = value.replace("..", ". ")
        value = re.sub(r"([.,])\1+", r"\1", value)
        value = re.sub(r"\s+([,.!?])", r"\1", value)
        value = re.sub(r"\s{2,}", " ", value)
        value = value.lstrip(",. ")
        return value.strip()
