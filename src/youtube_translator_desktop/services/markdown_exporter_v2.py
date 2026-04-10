from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from youtube_translator_desktop.models import SubtitleDocument

from .errors import ExportError


SLUG_PATTERN = re.compile(r"[^a-zA-Z0-9가-힣_-]+")


@dataclass(slots=True)
class MarkdownExporter:
    def export(
        self,
        subtitle_document: SubtitleDocument,
        output_dir: Path,
    ) -> tuple[Path, str]:
        markdown_text = subtitle_document.markdown_text
        output_path = self.export_named(
            markdown_text=markdown_text,
            title=subtitle_document.metadata.title or subtitle_document.metadata.video_id,
            output_dir=output_dir,
        )
        return output_path, markdown_text

    def export_named(
        self,
        markdown_text: str,
        title: str,
        output_dir: Path,
        suffix: str = "",
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._build_filename(title=title, suffix=suffix)
        output_path = output_dir / filename
        try:
            output_path.write_text(markdown_text, encoding="utf-8")
        except OSError as exc:
            raise ExportError(f"Markdown 파일 저장에 실패했습니다: {exc}") from exc
        return output_path

    def _build_filename(self, title: str, suffix: str = "") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = SLUG_PATTERN.sub("-", title).strip("-._")
        slug = slug or "youtube-summary"
        normalized_suffix = f"_{suffix}" if suffix else ""
        return f"{slug}{normalized_suffix}_{timestamp}.md"
