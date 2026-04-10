from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v11 import VttConverter as BaseVttConverter


BAD_TITLE_SUFFIXES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "의",
    "도",
    "만",
    "과",
    "와",
    "처럼",
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "보다",
    "거든요",
    "했어요",
    "합니다",
    "입니다",
    "돼요",
    "되요",
    "됩니다",
    "있어요",
    "있습니다",
)
MEANINGFUL_NOUN_LABELS = (
    "전략",
    "안정성",
    "수요",
    "병목",
    "인프라",
    "운영",
    "구조",
    "체계",
    "전환",
    "워크로드",
    "클라우드",
    "하이퍼스케일러",
    "네트워크",
    "다운로드",
    "저장소",
    "검증",
    "증명",
    "칩",
    "공정",
    "데이터센터",
    "클러스터",
    "CPU",
    "GPU",
    "TSMC",
    "GitHub",
    "애플",
    "마이크로소프트",
    "에이전트",
    "강화학습",
)


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _stable_fallback_title(self, block, exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        text = " ".join(turn.text for turn in block.turns)

        preferred_pairs = (
            ("수학", "증명", "수학 증명 접근"),
            ("마이크로소프트", "cpu", "마이크로소프트 전략과 CPU 수요"),
            ("github", "다운로드", "GitHub 다운로드 실패"),
            ("저장소", "다운로드", "저장소 다운로드"),
        )
        lowered_text = text.lower()
        for left, right, label in preferred_pairs:
            if left in lowered_text and right in lowered_text and label not in exclude:
                return label

        title = super()._stable_fallback_title(block, exclude=exclude)
        if title == "추가 논의":
            if "수학" in lowered_text or "증명" in lowered_text:
                return "수학 증명 접근"
            if "마이크로소프트" in lowered_text or "cpu" in lowered_text:
                return "마이크로소프트 전략"
            if "github" in lowered_text or "다운로드" in lowered_text:
                return "GitHub 다운로드 실패"
        return title

    def _is_bad_title(self, title: str) -> bool:
        if super()._is_bad_title(title):
            return True

        normalized_parts = [part.strip() for part in title.replace("/", " ").split() if part.strip()]
        if not normalized_parts:
            return True

        if any(part.endswith(BAD_TITLE_SUFFIXES) for part in normalized_parts):
            return True

        if not any(noun in title for noun in MEANINGFUL_NOUN_LABELS):
            return True

        last_part = normalized_parts[-1]
        if last_part.endswith(BAD_TITLE_SUFFIXES):
            return True

        return False
