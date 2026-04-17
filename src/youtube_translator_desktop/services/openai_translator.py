from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from youtube_translator_desktop.models import VideoMetadata

from .errors import TranslationError
from .subtitle_downloader_v3 import DownloadResult


@dataclass(slots=True)
class OpenAITranslator:
    api_key: str | None
    model: str = "gpt-5-mini"
    max_batch_chars: int = 6000

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def translate(self, download_result: DownloadResult, output_dir: Path, converter: Any) -> DownloadResult | None:
        if not self.is_enabled():
            return None

        english_path = self._find_english_vtt(download_result)
        if english_path is None:
            return None

        raw_segments = converter.parse_segments(english_path.read_text(encoding="utf-8"))
        segments = converter.merge_segments(raw_segments)
        if not segments:
            return None

        translated_texts = self._translate_batches([segment.text for segment in segments])
        translated_vtt = self._write_translated_vtt(download_result, output_dir, segments, translated_texts)
        metadata = self._translated_metadata(download_result.metadata)
        related_paths = [translated_vtt, *download_result.related_vtt_paths]
        return DownloadResult(metadata=metadata, vtt_path=translated_vtt, related_vtt_paths=related_paths)

    def _translate_batches(self, texts: list[str]) -> list[str]:
        translated: list[str] = []
        for batch_start, batch in self._batches(texts):
            translated.extend(self._translate_batch(batch_start, batch))
        if len(translated) != len(texts):
            raise TranslationError("OpenAI translation returned an unexpected number of segments.")
        return translated

    def _translate_batch(self, batch_start: int, batch: list[str]) -> list[str]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TranslationError("OpenAI package is not installed. Run `pip install -e .` again.") from exc

        items = [{"id": batch_start + index, "text": text} for index, text in enumerate(batch)]
        prompt = self._build_prompt(items)

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                input=prompt,
            )
        except Exception as exc:  # pragma: no cover - SDK/network errors vary.
            raise TranslationError(f"OpenAI translation failed: {exc}") from exc

        output_text = getattr(response, "output_text", "") or ""
        return self._parse_translation_response(output_text, batch)

    def _build_prompt(self, items: list[dict[str, str | int]]) -> str:
        return (
            "You are translating YouTube transcript segments from English to Korean.\n"
            "Translate every item into natural Korean full-translation prose.\n"
            "Do not summarize, omit, add speaker labels, add bullets, or add timestamps.\n"
            "Preserve technical terms such as CPU, GPU, TSMC, GitHub, RL, inference, and datacenter when useful.\n"
            "Return only valid JSON in this exact shape: "
            '{"translations":[{"id":0,"ko":"translated Korean text"}]}.\n\n'
            f"Items:\n{json.dumps(items, ensure_ascii=False)}"
        )

    def _parse_translation_response(self, output_text: str, fallback_batch: list[str]) -> list[str]:
        cleaned = output_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            payload = json.loads(cleaned)
            translations = payload.get("translations", [])
        except (json.JSONDecodeError, AttributeError) as exc:
            raise TranslationError("OpenAI translation response was not valid JSON.") from exc

        if not isinstance(translations, list) or len(translations) != len(fallback_batch):
            raise TranslationError("OpenAI translation response did not match the requested batch.")

        values: list[str] = []
        for item, fallback in zip(translations, fallback_batch):
            if not isinstance(item, dict):
                raise TranslationError("OpenAI translation response contained an invalid item.")
            value = str(item.get("ko") or "").strip()
            values.append(value or fallback)
        return values

    def _batches(self, texts: list[str]) -> list[tuple[int, list[str]]]:
        batches: list[tuple[int, list[str]]] = []
        current: list[str] = []
        current_start = 0
        current_chars = 0

        for index, text in enumerate(texts):
            projected = current_chars + len(text)
            if current and projected > self.max_batch_chars:
                batches.append((current_start, current))
                current = []
                current_start = index
                current_chars = 0
            current.append(text)
            current_chars += len(text)

        if current:
            batches.append((current_start, current))
        return batches

    def _find_english_vtt(self, download_result: DownloadResult) -> Path | None:
        candidates = []
        for path in download_result.related_vtt_paths:
            name = path.name.lower()
            if ".en." in name or ".en-" in name or name.endswith(".en.vtt"):
                candidates.append(path)
        return candidates[0] if candidates else None

    def _write_translated_vtt(
        self,
        download_result: DownloadResult,
        output_dir: Path,
        segments: list[Any],
        translated_texts: list[str],
    ) -> Path:
        work_dir = output_dir / "downloads"
        work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / f"{download_result.metadata.video_id}.openai-ko.vtt"

        lines = ["WEBVTT", ""]
        for index, (segment, text) in enumerate(zip(segments, translated_texts), start=1):
            lines.append(str(index))
            lines.append(f"{segment.start} --> {segment.end}")
            lines.append(text.replace("\n", " ").strip())
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _translated_metadata(self, metadata: VideoMetadata) -> VideoMetadata:
        return replace(metadata, language_code="openai-ko")
