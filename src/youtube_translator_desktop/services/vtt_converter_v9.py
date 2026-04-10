from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v5 import TopicBlock
from .vtt_converter_v8 import TopicSection, VttConverter as BaseVttConverter


GENERIC_TITLES = {
    "주요 논의",
    "클라우드 인프라",
    "워크로드 변화",
    "병목 문제",
}
BAD_FALLBACK_KEYWORDS = ("보입니다", "있습니다", "됩니다", "늘었습니다", "줄었습니다", "발생합니다", "커졌습니다")


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _build_topic_sections(self, topic_blocks: list[TopicBlock]) -> list[TopicSection]:
        refined_blocks = self._refine_topic_blocks(topic_blocks)
        sections: list[TopicSection] = []
        seen_titles: dict[str, int] = {}

        for block in refined_blocks:
            title = self._finalize_title(block, seen_titles)
            paragraphs = self._group_paragraphs(block)
            sections.append(TopicSection(title=title, paragraphs=paragraphs))
        return sections

    def _refine_topic_blocks(self, topic_blocks: list[TopicBlock]) -> list[TopicBlock]:
        if not topic_blocks:
            return []

        refined: list[TopicBlock] = [topic_blocks[0]]
        for block in topic_blocks[1:]:
            previous = refined[-1]
            if self._should_merge_blocks(previous, block):
                refined[-1] = TopicBlock(
                    title=self._make_topic_title(previous.turns + block.turns),
                    turns=previous.turns + block.turns,
                )
            else:
                refined.append(block)
        return refined

    def _should_merge_blocks(self, previous: TopicBlock, current: TopicBlock) -> bool:
        if previous.title == current.title:
            return True
        if self._is_meaningless_title(current.title):
            return True

        previous_keywords = self._keywords(" ".join(turn.text for turn in previous.turns[-2:]))
        current_keywords = self._keywords(" ".join(turn.text for turn in current.turns[:2]))
        similarity = self._similarity(previous_keywords, current_keywords)
        return similarity >= 0.35 and len(current.turns) <= 2

    def _finalize_title(self, block: TopicBlock, seen_titles: dict[str, int]) -> str:
        labels = self._extract_title_labels(block)
        if not labels:
            title = self._fallback_title_from_text(block)
        elif len(labels) == 1:
            title = labels[0]
        else:
            title = f"{labels[0]}{self._topic_joiner(labels[0])}{labels[1]}"

        if self._is_meaningless_title(title) and labels:
            title = labels[0]

        count = seen_titles.get(title, 0)
        if count == 0:
            seen_titles[title] = 1
            return title

        extra_label = next((label for label in labels[1:] if label not in title), None)
        if extra_label:
            updated = f"{title} / {extra_label}"
            seen_titles[updated] = seen_titles.get(updated, 0) + 1
            return updated

        seen_titles[title] = count + 1
        return f"{title} {count + 1}"

    def _fallback_title_from_text(self, block: TopicBlock) -> str:
        first_text = block.turns[0].text if block.turns else ""
        keywords = sorted(
            (word for word in self._keywords(first_text) if word not in BAD_FALLBACK_KEYWORDS),
            key=lambda item: (-len(item), item),
        )
        if not keywords:
            return "추가 논의"

        picked = [self._display_keyword(word) for word in keywords[:2]]
        if len(picked) == 1:
            return picked[0]
        return f"{picked[0]}{self._topic_joiner(picked[0])}{picked[1]}"

    def _extract_title_labels(self, block: TopicBlock) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()
        text = " ".join(turn.text for turn in block.turns)
        for token in self._title_tokens(text):
            label = self._keyword_to_title_label(token)
            if label and label not in seen:
                labels.append(label)
                seen.add(label)

        if labels:
            labels.sort(key=lambda item: (-self._title_priority(item, text), item))
        return labels[:3]

    def _title_priority(self, label: str, text: str) -> int:
        score = 0
        if label in text:
            score += 8
        keywords = {
            "GitHub 안정성": ("github", "깃허브", "다운로드", "실패"),
            "마이크로소프트 전략": ("microsoft", "마이크로소프트", "외부", "판매"),
            "CPU 수요": ("cpu", "수요", "요청"),
            "GPU 병목": ("gpu", "병목"),
            "클러스터 운영": ("클러스터", "cluster", "운영"),
            "추론 인프라": ("추론", "inference"),
            "에이전트 워크로드": ("에이전트", "agent"),
            "강화학습 워크로드": ("강화학습", "rl"),
            "배포 구조": ("배포", "deploy"),
        }.get(label, ())
        lower_text = text.lower()
        score += sum(3 for keyword in keywords if keyword in lower_text)
        return score

    def _is_meaningless_title(self, title: str) -> bool:
        if title in GENERIC_TITLES:
            return True
        return len(title.strip()) <= 3
