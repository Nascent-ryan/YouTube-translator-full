from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from youtube_translator_desktop.models import GenerationResult

from .markdown_exporter_v2 import MarkdownExporter
from .openai_translator import OpenAITranslator
from .original_markdown_builder import OriginalMarkdownBuilder
from .postprocessor_v2 import PostProcessor
from .subtitle_downloader_v3 import SubtitleDownloader
from .vtt_converter_v13 import VttConverter


@dataclass(slots=True)
class GenerationPipeline:
    subtitle_downloader: SubtitleDownloader
    vtt_converter: VttConverter
    postprocessor: PostProcessor
    markdown_exporter: MarkdownExporter
    original_markdown_builder: OriginalMarkdownBuilder
    openai_translator: OpenAITranslator | None = None

    def run(self, url: str, output_dir: Path) -> GenerationResult:
        download_result = self.subtitle_downloader.download(url, output_dir)
        warnings: list[str] = []
        conversion_source = download_result
        if self.openai_translator and self.openai_translator.is_enabled():
            try:
                translated_result = self.openai_translator.translate(download_result, output_dir, self.vtt_converter)
                if translated_result:
                    conversion_source = translated_result
            except Exception as exc:
                warnings.append(f"OpenAI translation skipped: {exc}")

        subtitle_document = self.vtt_converter.convert(conversion_source)
        subtitle_document = self.postprocessor.process(subtitle_document)
        output_path, markdown_text = self.markdown_exporter.export(subtitle_document, output_dir)
        original_markdown_text = self.original_markdown_builder.build(download_result, self.vtt_converter)
        original_output_path = None
        if original_markdown_text:
            original_output_path = self.markdown_exporter.export_named(
                markdown_text=original_markdown_text,
                title=subtitle_document.metadata.title or subtitle_document.metadata.video_id,
                output_dir=output_dir,
                suffix="english-original",
            )
        return GenerationResult(
            subtitle_document=subtitle_document,
            output_path=output_path,
            markdown_text=markdown_text,
            original_output_path=original_output_path,
            original_markdown_text=original_markdown_text,
            warnings=warnings,
        )
