from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v12 import VttConverter as BaseVttConverter


CORE_NOUN_LABELS = {
    "github": "GitHub 다운로드 실패",
    "다운로드": "다운로드 실패",
    "저장소": "저장소 다운로드",
    "microsoft": "마이크로소프트 전략",
    "마이크로소프트": "마이크로소프트 전략",
    "cpu": "CPU 수요",
    "gpu": "GPU 병목",
    "병목": "GPU 병목",
    "cluster": "클러스터 운영",
    "클러스터": "클러스터 운영",
    "inference": "추론 인프라",
    "추론": "추론 인프라",
    "deploy": "배포 구조",
    "배포": "배포 구조",
    "agent": "에이전트 워크로드",
    "에이전트": "에이전트 워크로드",
    "rl": "강화학습 워크로드",
    "강화학습": "강화학습 워크로드",
    "수학": "수학 증명 접근",
    "증명": "수학 증명 접근",
    "검증": "검증 구조",
    "검증기": "검증 구조",
    "생성기": "생성기와 검증기",
    "network": "네트워크 이슈",
    "네트워크": "네트워크 이슈",
    "tsmc": "TSMC 공정 전환",
    "3나노미터": "3나노미터 전환",
    "공정": "공정 전환",
    "칩": "AI 칩 전환",
    "ai": "AI 칩 전환",
    "애플": "애플 칩 전략",
    "cloud": "클라우드 인프라",
    "하이퍼스케일러": "하이퍼스케일러 전략",
    "네오클라우드": "네오클라우드 전략",
}
WEAK_NOUN_LABELS = {
    "구조",
    "체계",
    "인프라",
    "운영",
    "전환",
    "전략",
    "이슈",
    "논의",
}
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


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _finalize_title(self, block, seen_titles: dict[str, int]) -> str:
        title = self._force_core_title(block) or self._build_noun_title(block)
        if self._is_bad_title(title):
            title = "추가 논의"

        count = seen_titles.get(title, 0)
        if count == 0:
            seen_titles[title] = 1
            return title

        alternate = self._build_noun_title(block, exclude={title})
        if alternate != title and not self._is_bad_title(alternate):
            seen_titles[alternate] = seen_titles.get(alternate, 0) + 1
            return alternate

        seen_titles[title] = count + 1
        return f"{title} {count + 1}"

    def _force_core_title(self, block) -> str | None:
        text = " ".join(turn.text for turn in block.turns).lower()
        if "github" in text and "다운로드" in text and "마이크로소프트" in text:
            return "GitHub 다운로드 실패와 마이크로소프트 전략"
        if "github" in text and "다운로드" in text:
            return "GitHub 다운로드 실패"
        if "마이크로소프트" in text and "cpu" in text:
            return "마이크로소프트 전략과 CPU 수요"
        if "cpu" in text and "에이전트" in text:
            return "CPU 수요와 에이전트 워크로드"
        return None

    def _build_noun_title(self, block, exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        text = " ".join(turn.text for turn in block.turns)
        labels: list[str] = []
        seen: set[str] = set(exclude)

        for token in self._title_tokens(text):
            label = CORE_NOUN_LABELS.get(token)
            if label and label not in seen:
                labels.append(label)
                seen.add(label)

        if labels:
            ranked = sorted(labels, key=lambda item: (-self._noun_label_score(item, text), item))
            if len(ranked) == 1:
                return ranked[0]
            return f"{ranked[0]}{self._topic_joiner(ranked[0])}{ranked[1]}"

        fallback = self._stable_fallback_title(block, exclude=exclude)
        return fallback

    def _noun_label_score(self, label: str, text: str) -> int:
        score = 0
        lower_text = text.lower()
        for token, mapped in CORE_NOUN_LABELS.items():
            if mapped == label and token in lower_text:
                score += 3
        if any(weak in label for weak in WEAK_NOUN_LABELS):
            score -= 1
        if label in text:
            score += 2
        return score

    def _is_bad_title(self, title: str) -> bool:
        if not title or len(title.strip()) <= 3:
            return True
        parts = [part.strip() for part in title.replace("/", " ").split() if part.strip()]
        if not parts:
            return True
        if not any(
            label in title
            for label in (
                "GitHub",
                "다운로드",
                "마이크로소프트",
                "CPU",
                "GPU",
                "클러스터",
                "추론",
                "배포",
                "에이전트",
                "강화학습",
                "수학",
                "증명",
                "검증",
                "TSMC",
                "3나노미터",
                "칩",
                "애플",
                "클라우드",
                "하이퍼스케일러",
                "네오클라우드",
                "네트워크",
            )
        ):
            return True
        if parts[-1].endswith(BAD_TITLE_SUFFIXES):
            return True
        return False
