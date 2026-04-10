from __future__ import annotations

import re
from dataclasses import dataclass

from .vtt_converter_v5 import TopicBlock
from .vtt_converter_v9 import VttConverter as BaseVttConverter


BAD_TITLE_ENDINGS = (
    "입니다",
    "입니다와",
    "같아요",
    "거든요",
    "봤어요",
    "했어요",
    "했거든요",
    "것뿐입니다",
    "마찬가지입니다",
    "생각했어요",
    "보입니다",
    "됩니다",
    "있어요",
    "있습니다",
)
BAD_TITLE_TOKENS = {
    "그리고",
    "그런데",
    "그러니까",
    "이제",
    "정말",
    "아마",
    "완전히",
    "저는",
    "그게",
    "그건",
    "이것은",
    "마찬가지입니다",
    "생각했어요",
}
NATURAL_FALLBACK_LABELS = {
    "네트워크": "네트워크 이슈",
    "내부": "내부 배포 체계",
    "배포": "배포 체계",
    "저장소": "저장소 다운로드",
    "다운로드": "다운로드 실패",
    "검증기": "검증 구조",
    "생성기": "생성기와 검증기",
    "수학": "수학 증명 접근",
    "3나노미터": "3나노미터 전환",
    "칩": "칩 전환",
    "tsmc": "TSMC 공정 전환",
    "애플": "애플 칩 전략",
}
HANGUL_WORD_PATTERN = re.compile(r"[가-힣A-Za-z0-9-]{2,}")


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _should_merge_blocks(self, previous: TopicBlock, current: TopicBlock) -> bool:
        if super()._should_merge_blocks(previous, current):
            return True
        return self._is_invalid_title_candidate(current)

    def _finalize_title(self, block: TopicBlock, seen_titles: dict[str, int]) -> str:
        title = super()._finalize_title(block, seen_titles={})
        if self._is_bad_title(title):
            title = self._stable_fallback_title(block)
        if self._is_bad_title(title):
            title = "추가 논의"

        count = seen_titles.get(title, 0)
        if count == 0:
            seen_titles[title] = 1
            return title

        alternate = self._stable_fallback_title(block, exclude={title})
        if alternate and alternate != title and not self._is_bad_title(alternate):
            seen_titles[alternate] = seen_titles.get(alternate, 0) + 1
            return alternate

        seen_titles[title] = count + 1
        return f"{title} {count + 1}"

    def _is_invalid_title_candidate(self, block: TopicBlock) -> bool:
        generated = self._make_topic_title(block.turns)
        return self._is_bad_title(generated)

    def _is_bad_title(self, title: str) -> bool:
        if not title or len(title.strip()) <= 3:
            return True
        if any(token in title for token in BAD_TITLE_TOKENS):
            return True
        if any(title.endswith(ending) for ending in BAD_TITLE_ENDINGS):
            return True

        words = [word for word in HANGUL_WORD_PATTERN.findall(title) if word]
        if not words:
            return True

        bad_word_count = 0
        for word in words:
            if any(word.endswith(ending) for ending in BAD_TITLE_ENDINGS):
                bad_word_count += 1
            if word in BAD_TITLE_TOKENS:
                bad_word_count += 1

        return bad_word_count >= 1

    def _stable_fallback_title(self, block: TopicBlock, exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        text = " ".join(turn.text for turn in block.turns)
        keywords = [word for word in self._keywords(text) if word not in BAD_TITLE_TOKENS]

        labels: list[str] = []
        seen: set[str] = set(exclude)
        for keyword in keywords:
            label = NATURAL_FALLBACK_LABELS.get(keyword)
            if label and label not in seen:
                labels.append(label)
                seen.add(label)

        if labels:
            if len(labels) == 1:
                return labels[0]
            return f"{labels[0]}{self._topic_joiner(labels[0])}{labels[1]}"

        clean_words = [
            self._display_keyword(word)
            for word in keywords
            if len(word) >= 2 and not self._looks_like_sentence_fragment(word)
        ]
        if not clean_words:
            return "추가 논의"
        if len(clean_words) == 1:
            return clean_words[0]
        return f"{clean_words[0]}{self._topic_joiner(clean_words[0])}{clean_words[1]}"

    def _looks_like_sentence_fragment(self, word: str) -> bool:
        return any(word.endswith(ending) for ending in BAD_TITLE_ENDINGS) or word in BAD_TITLE_TOKENS
