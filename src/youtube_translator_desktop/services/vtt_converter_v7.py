from __future__ import annotations

from dataclasses import dataclass

from .vtt_converter_v5 import DialogueTurn, VttSegment
from .vtt_converter_v6 import VttConverter as BaseVttConverter


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def _build_turns(
        self,
        translated_segments: list[VttSegment],
        original_segments: list[VttSegment],
    ) -> list[DialogueTurn]:
        turns: list[DialogueTurn] = []

        for segment in translated_segments:
            original = self._find_matching_original(segment, original_segments)
            original_text = original.text if original else ""
            previous_role = turns[-1].speaker if turns else None
            role = self._classify_role(segment.text, original_text, previous_role)
            turns.append(
                DialogueTurn(
                    speaker=role,
                    text=segment.text,
                    original_text=original.text if original else None,
                )
            )
        return turns

    def _render_topic_block(self, block, index: int) -> str:
        lines = [f"### 주제 {index}. {block.title}"]
        current_role = None
        for turn in block.turns:
            if turn.speaker != current_role:
                lines.append(f"**{turn.speaker}**")
                current_role = turn.speaker
            lines.append(f"- {turn.text}")
        return "\n".join(lines)

    def _classify_role(self, translated_text: str, original_text: str, previous_role: str | None) -> str:
        if self._contains_question_signal(translated_text, original_text):
            return "Q"
        if self._looks_like_host_prompt(translated_text, original_text):
            return "Q"
        if previous_role == "Q" and self._is_short_follow_up(translated_text, original_text):
            return "Q"
        return "A"
