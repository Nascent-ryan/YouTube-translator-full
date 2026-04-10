from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .services.markdown_exporter_v2 import MarkdownExporter
from .services.original_markdown_builder import OriginalMarkdownBuilder
from .services.pipeline import GenerationPipeline
from .services.postprocessor_v2 import PostProcessor
from .services.subtitle_downloader_v3 import SubtitleDownloader
from .services.vtt_converter_v13 import VttConverter
from .ui.main_window import MainWindow


def build_pipeline(config: AppConfig) -> GenerationPipeline:
    return GenerationPipeline(
        subtitle_downloader=SubtitleDownloader(cookies_path=config.cookies_path),
        vtt_converter=VttConverter(),
        postprocessor=PostProcessor(),
        markdown_exporter=MarkdownExporter(),
        original_markdown_builder=OriginalMarkdownBuilder(),
    )


def main() -> int:
    config = AppConfig.load()
    app = QApplication(sys.argv)
    window = MainWindow(
        pipeline=build_pipeline(config),
        default_output_dir=config.default_output_dir,
        default_cookies_path=config.cookies_path,
    )
    window.show()
    return app.exec()
