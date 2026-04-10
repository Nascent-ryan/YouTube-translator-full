from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v10 import VttConverter as BaseVttConverter


EXTRA_BAD_TITLE_TOKENS = {
    "식이었거든요",
    "해보자",
    "이동하",
    "같은",
    "맥락입니다",
    "생각",
    "부족한",
    "만들어야",
}
EXTRA_BAD_TITLE_ENDINGS = ("거든요", "했어요", "합니다", "입니다", "해요", "하", "자")
EXTRA_FALLBACK_LABELS = {
    "수학": "수학 증명 접근",
    "증명": "수학 증명 접근",
    "tsmc": "TSMC 공정 전환",
    "3나노미터": "3나노미터 전환",
    "ai": "AI 칩 전환",
    "칩": "AI 칩 전환",
    "공정": "공정 전환",
}


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _is_bad_title(self, title: str) -> bool:
        if super()._is_bad_title(title):
            return True

        words = title.replace("/", " ").split()
        for word in words:
            if word in EXTRA_BAD_TITLE_TOKENS:
                return True
            if any(word.endswith(ending) for ending in EXTRA_BAD_TITLE_ENDINGS):
                return True
        return False

    def _stable_fallback_title(self, block, exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        text = " ".join(turn.text for turn in block.turns)
        keywords = [word for word in self._keywords(text) if word not in EXTRA_BAD_TITLE_TOKENS]

        labels: list[str] = []
        seen: set[str] = set(exclude)
        for keyword in keywords:
            label = EXTRA_FALLBACK_LABELS.get(keyword)
            if label and label not in seen:
                labels.append(label)
                seen.add(label)

        if labels:
            if len(labels) == 1:
                return labels[0]
            return f"{labels[0]}{self._topic_joiner(labels[0])}{labels[1]}"

        return super()._stable_fallback_title(block, exclude=exclude)

    def _looks_like_sentence_fragment(self, word: str) -> bool:
        if super()._looks_like_sentence_fragment(word):
            return True
        if word in EXTRA_BAD_TITLE_TOKENS:
            return True
        return any(word.endswith(ending) for ending in EXTRA_BAD_TITLE_ENDINGS)
