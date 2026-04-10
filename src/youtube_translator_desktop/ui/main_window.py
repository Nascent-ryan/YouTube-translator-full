from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from youtube_translator_desktop.models import GenerationResult
from youtube_translator_desktop.services.errors import AppError
from youtube_translator_desktop.services.pipeline import GenerationPipeline
from youtube_translator_desktop.services.url_utils import extract_video_id


class WorkerSignals(QObject):
    success = Signal(object)
    error = Signal(str)


class GenerationWorker(QRunnable):
    def __init__(
        self,
        pipeline: GenerationPipeline,
        url: str,
        output_dir: Path,
        cookies_path: Path | None,
        signals: WorkerSignals,
    ) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.url = url
        self.output_dir = output_dir
        self.cookies_path = cookies_path
        self.signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            self.pipeline.subtitle_downloader.cookies_path = self.cookies_path
            result = self.pipeline.run(self.url, self.output_dir)
        except AppError as exc:
            self.signals.error.emit(str(exc))
        except Exception as exc:
            self.signals.error.emit(f"처리 중 예기치 못한 오류가 발생했습니다: {exc}")
        else:
            self.signals.success.emit(result)


class MainWindow(QMainWindow):
    def __init__(
        self,
        pipeline: GenerationPipeline,
        default_output_dir: Path,
        default_cookies_path: Path | None,
    ) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.default_output_dir = default_output_dir
        self.default_cookies_path = default_cookies_path
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("YouTube Translator (Full version)")
        self.resize(960, 720)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("YouTube Translator (Full version)")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setClearButtonEnabled(True)
        layout.addWidget(self.url_input)

        output_layout = QHBoxLayout()
        self.output_input = QLineEdit(str(self.default_output_dir))
        browse_button = QPushButton("폴더 선택")
        browse_button.clicked.connect(self._choose_output_dir)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_button)
        layout.addLayout(output_layout)

        cookies_layout = QHBoxLayout()
        self.cookies_input = QLineEdit(str(self.default_cookies_path) if self.default_cookies_path else "")
        cookies_browse_button = QPushButton("쿠키 선택")
        cookies_browse_button.clicked.connect(self._choose_cookies_file)
        cookies_layout.addWidget(self.cookies_input)
        cookies_layout.addWidget(cookies_browse_button)
        layout.addLayout(cookies_layout)

        button_layout = QHBoxLayout()
        self.run_button = QPushButton("변환 시작")
        self.run_button.clicked.connect(self._start_generation)
        self.run_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button_layout.addWidget(self.run_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.status_label = QLabel("대기 중")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.status_label)

        self.preview = QTextBrowser()
        self.preview.setPlaceholderText("결과가 여기 표시됩니다.")
        layout.addWidget(self.preview, stretch=1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.output_input.text())
        if directory:
            self.output_input.setText(directory)

    def _start_generation(self) -> None:
        url = self.url_input.text().strip()
        try:
            extract_video_id(url)
        except AppError as exc:
            self._show_error(str(exc))
            return

        output_dir = Path(self.output_input.text().strip() or self.default_output_dir)
        cookies_text = self.cookies_input.text().strip()
        cookies_path = Path(cookies_text) if cookies_text else None
        signals = WorkerSignals()
        signals.success.connect(self._on_success)
        signals.error.connect(self._on_error)

        worker = GenerationWorker(
            pipeline=self.pipeline,
            url=url,
            output_dir=output_dir,
            cookies_path=cookies_path,
            signals=signals,
        )
        self.run_button.setEnabled(False)
        self.status_label.setText("자막 다운로드 및 Markdown 변환 중...")
        self.statusBar().showMessage("작업 진행 중")
        self.preview.clear()
        self.thread_pool.start(worker)

    def _choose_cookies_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "쿠키 파일 선택",
            str(Path(self.cookies_input.text()).parent) if self.cookies_input.text().strip() else str(Path.cwd()),
            "Text Files (*.txt);;All Files (*.*)",
        )
        if path:
            self.cookies_input.setText(path)

    def _on_success(self, result: GenerationResult) -> None:
        self.run_button.setEnabled(True)
        self.status_label.setText(f"완료: {result.output_path}")
        self.statusBar().showMessage("완료")
        self.preview.setMarkdown(result.markdown_text)

    def _on_error(self, message: str) -> None:
        self.run_button.setEnabled(True)
        self.status_label.setText("실패")
        self.statusBar().showMessage("오류")
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "오류", message)
