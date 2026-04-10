from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v5 import DialogueTurn, VttConverter as BaseVttConverter, VttSegment


HOST_PROMPT_HINTS_KO = (
    "궁금",
    "설명해",
    "설명해주",
    "말씀해주",
    "어떻게 보",
    "왜 그렇",
    "맞나요",
    "볼까요",
    "보셨",
    "이야기해주",
    "공유해주",
    "예를 들어",
    "그럼",
)
HOST_PROMPT_HINTS_EN = (
    "walk me through",
    "tell us",
    "can you explain",
    "help us understand",
    "what do you think",
    "how do you see",
    "why is that",
)
QUESTION_HINTS_KO = ("왜", "어떻게", "무엇", "얼마", "가능한가", "있나", "궁금", "맞나요", "보셨", "설명해", "그럼")
QUESTION_HINTS_EN = ("why", "how", "what", "can you", "do you", "are there", "could you", "would you", "have you")
GUEST_STATEMENT_HINTS_KO = (
    "입니다",
    "있습니다",
    "됩니다",
    "보입니다",
    "실제로",
    "저희도",
    "늘었습니다",
    "늘어납니다",
    "중요합니다",
    "불안정합니다",
    "팔아버렸",
    "의미합니다",
    "만듭니다",
)
GUEST_STATEMENT_HINTS_EN = (
    "because",
    "therefore",
    "we see",
    "it means",
    "the reality is",
    "in practice",
)


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _find_matching_original(
        self,
        translated_segment: VttSegment,
        original_segments: list[VttSegment],
    ) -> VttSegment | None:
        target = self._to_seconds(translated_segment.start)
        best_match: VttSegment | None = None
        best_distance = 9999.0

        for original in original_segments:
            distance = abs(self._to_seconds(original.start) - target)
            if distance <= 8 and distance < best_distance:
                best_match = original
                best_distance = distance

        return best_match

    def _build_turns(
        self,
        translated_segments: list[VttSegment],
        original_segments: list[VttSegment],
    ) -> list[DialogueTurn]:
        turns: list[DialogueTurn] = []

        for segment in translated_segments:
            original = self._find_matching_original(segment, original_segments)
            original_text = original.text if original else ""
            previous_speaker = turns[-1].speaker if turns else None
            previous_text = turns[-1].text if turns else ""
            speaker = self._classify_speaker(
                translated_text=segment.text,
                original_text=original_text,
                previous_speaker=previous_speaker,
                previous_text=previous_text,
            )
            turns.append(
                DialogueTurn(
                    speaker=speaker,
                    text=segment.text,
                    original_text=original.text if original else None,
                )
            )
        return turns

    def _classify_speaker(
        self,
        translated_text: str,
        original_text: str,
        previous_speaker: str | None,
        previous_text: str,
    ) -> str:
        host_score, guest_score = self._speaker_scores(translated_text, original_text)

        # Interview flow heuristic: once the host asks, the next substantial line is usually the guest.
        if previous_speaker == "진행자" and host_score < 4:
            guest_score += 2
        elif previous_speaker == "게스트" and guest_score >= host_score:
            guest_score += 1

        # Short follow-up prompts are usually still the host.
        if previous_speaker == "진행자" and self._is_short_follow_up(translated_text, original_text):
            host_score += 2

        # If the previous line was a clear question, bias the current line toward the guest.
        if previous_text and self._contains_question_signal(previous_text, "") and host_score < 4:
            guest_score += 4

        if previous_speaker == "진행자" and not self._contains_question_signal(translated_text, original_text):
            guest_score += 2

        return "진행자" if host_score > guest_score else "게스트"

    def _speaker_scores(self, translated_text: str, original_text: str) -> tuple[int, int]:
        host_score = 0
        guest_score = 0

        if self._contains_question_signal(translated_text, original_text):
            host_score += 4
        if self._looks_like_host_prompt(translated_text, original_text):
            host_score += 3
        if self._is_short_follow_up(translated_text, original_text):
            host_score += 2

        translated_word_count = len(translated_text.split())
        original_word_count = len(original_text.split())
        if translated_word_count <= 12 or original_word_count <= 12:
            host_score += 1
        if translated_word_count >= 18 or original_word_count >= 18:
            guest_score += 2

        if self._looks_like_guest_statement(translated_text, original_text):
            guest_score += 3
        if not self._contains_question_signal(translated_text, original_text):
            guest_score += 1

        return host_score, guest_score

    def _contains_question_signal(self, translated_text: str, original_text: str) -> bool:
        lower_ko = translated_text.lower()
        lower_en = original_text.lower()
        if "?" in translated_text or "?" in original_text:
            return True
        if any(token in lower_ko for token in QUESTION_HINTS_KO):
            return True
        return any(token in lower_en for token in QUESTION_HINTS_EN)

    def _looks_like_host_prompt(self, translated_text: str, original_text: str) -> bool:
        lower_ko = translated_text.lower()
        lower_en = original_text.lower()
        if any(token in lower_ko for token in HOST_PROMPT_HINTS_KO):
            return True
        return any(token in lower_en for token in HOST_PROMPT_HINTS_EN)

    def _looks_like_guest_statement(self, translated_text: str, original_text: str) -> bool:
        lower_ko = translated_text.lower()
        lower_en = original_text.lower()
        if any(token in lower_ko for token in GUEST_STATEMENT_HINTS_KO):
            return True
        return any(token in lower_en for token in GUEST_STATEMENT_HINTS_EN)

    def _is_short_follow_up(self, translated_text: str, original_text: str) -> bool:
        lower_ko = translated_text.lower()
        lower_en = original_text.lower()
        cue = (
            lower_ko.startswith(("그럼", "그러면", "그런데", "최근", "혹시"))
            or lower_en.startswith(("so ", "then ", "and ", "but "))
        )
        return cue and max(len(translated_text.split()), len(original_text.split())) <= 16
