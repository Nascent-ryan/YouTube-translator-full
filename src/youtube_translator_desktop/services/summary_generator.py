from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from youtube_translator_desktop.models import SummaryDocument, TranscriptDocument

from .errors import SummarizationError


SYSTEM_PROMPT = """당신은 유튜브 영상 내용을 한국어로 정리하는 전문 에디터입니다.
목표는 직역보다 이해하기 쉬운 한국어 정리문을 만드는 것입니다.
출력은 반드시 JSON 객체로만 반환하세요.
필수 키:
- video_info: 문자열 배열
- overall_summary: 문자열
- detailed_notes: 문자열 배열
- key_points: 문자열 배열
- notable_quotes: 문자열 배열
규칙:
- 전체 응답은 한국어로 작성합니다.
- 중요한 표현은 원문: "..." 형식으로 notable_quotes에 넣습니다.
- 과장하거나 추측하지 말고 제공된 자막 범위 안에서만 정리합니다.
- detailed_notes는 영상 전개 순서를 따르며 4개 이상 작성합니다.
- key_points는 짧고 핵심적으로 작성합니다.
"""


@dataclass(slots=True)
class SummaryGenerator:
    api_key: str
    model: str
    chunk_character_limit: int = 6000
    _client: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._client = OpenAI(api_key=self.api_key) if self.api_key else None

    def generate(self, transcript: TranscriptDocument) -> SummaryDocument:
        if not self.api_key:
            raise SummarizationError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인해 주세요.")

        chunks = self._split_text(transcript.transcript_text)
        partial_summaries: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            user_prompt = self._build_chunk_prompt(transcript, chunk, index, len(chunks))
            partial_summaries.append(self._invoke_model(user_prompt))

        final_prompt = self._build_merge_prompt(transcript, partial_summaries)
        raw_response = self._invoke_model(final_prompt)
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise SummarizationError("모델 응답을 JSON으로 해석하지 못했습니다.") from exc

        return SummaryDocument(
            video_info=payload.get("video_info", []),
            overall_summary=payload.get("overall_summary", "").strip(),
            detailed_notes=payload.get("detailed_notes", []),
            key_points=payload.get("key_points", []),
            notable_quotes=payload.get("notable_quotes", []),
            source_language=transcript.metadata.language_code,
            raw_response=raw_response,
        )

    def _invoke_model(self, user_prompt: str) -> str:
        assert self._client is not None
        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                ],
            )
        except RateLimitError as exc:
            raise SummarizationError("OpenAI API rate limit에 걸렸습니다. 잠시 후 다시 시도해 주세요.") from exc
        except APIConnectionError as exc:
            raise SummarizationError("OpenAI API 연결에 실패했습니다. 네트워크 상태를 확인해 주세요.") from exc
        except APIError as exc:
            raise SummarizationError(f"OpenAI API 오류가 발생했습니다: {exc}") from exc
        except Exception as exc:
            raise SummarizationError(f"요약 생성 중 알 수 없는 오류가 발생했습니다: {exc}") from exc

        return response.output_text.strip()

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_character_limit:
            return [text]

        chunks: list[str] = []
        current: list[str] = []
        current_length = 0

        for paragraph in text.splitlines():
            candidate = paragraph.strip()
            if not candidate:
                continue

            if current and current_length + len(candidate) + 1 > self.chunk_character_limit:
                chunks.append("\n".join(current))
                current = [candidate]
                current_length = len(candidate)
            else:
                current.append(candidate)
                current_length += len(candidate) + 1

        if current:
            chunks.append("\n".join(current))

        return chunks

    @staticmethod
    def _build_chunk_prompt(
        transcript: TranscriptDocument,
        chunk_text: str,
        chunk_index: int,
        total_chunks: int,
    ) -> str:
        return f"""다음은 YouTube 영상 자막의 일부입니다.
영상 URL: {transcript.metadata.url}
영상 ID: {transcript.metadata.video_id}
자막 언어: {transcript.metadata.language_code or "unknown"}
현재 chunk: {chunk_index}/{total_chunks}

이 chunk에 대해서만 한국어 정리 초안을 JSON으로 작성하세요.
video_info는 이 chunk 기준 메모 수준으로 간단히 작성하고, detailed_notes는 최소 3개 작성하세요.

자막:
{chunk_text}
"""

    @staticmethod
    def _build_merge_prompt(transcript: TranscriptDocument, partial_summaries: list[str]) -> str:
        joined = "\n\n".join(
            f"[chunk {index}]\n{content}" for index, content in enumerate(partial_summaries, start=1)
        )
        return f"""아래는 YouTube 영상 자막 chunk별 한국어 정리 초안들입니다.
이 초안들을 하나의 최종 결과로 병합해 JSON으로 반환하세요.

최종 결과 규칙:
- video_info에는 영상 URL, 영상 ID, 자막 언어, 자막 소스(youtube_transcript)를 반영하세요.
- overall_summary는 2~4문단 정도로 자연스럽게 작성하세요.
- detailed_notes는 시간 순서대로 5개 이상 작성하세요.
- key_points는 4~8개 작성하세요.
- notable_quotes는 원문 표현이 드러나는 항목만 남기고 각 항목을 `원문: "..." - 설명` 형식으로 작성하세요.

영상 URL: {transcript.metadata.url}
영상 ID: {transcript.metadata.video_id}
자막 언어: {transcript.metadata.language_code or "unknown"}

초안들:
{joined}
"""
