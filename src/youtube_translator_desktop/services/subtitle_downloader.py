from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from youtube_translator_desktop.models import VideoMetadata

from .errors import TranscriptError
from .url_utils import extract_video_id


@dataclass(slots=True)
class DownloadResult:
    metadata: VideoMetadata
    vtt_path: Path


@dataclass(slots=True)
class SubtitleDownloader:
    subtitle_languages: tuple[str, ...] = ("ko", "en", "en-US", "en-GB")
    cookies_path: Path | None = None

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        video_id = extract_video_id(url)
        yt_dlp = self._resolve_yt_dlp()
        work_dir = output_dir / "downloads"
        work_dir.mkdir(parents=True, exist_ok=True)

        metadata = self._fetch_metadata(yt_dlp, url, video_id)
        output_template = str(work_dir / "%(id)s.%(ext)s")
        command = [
            *yt_dlp,
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-langs",
            ",".join(self.subtitle_languages),
            "--sub-format",
            "vtt",
            "--output",
            output_template,
            url,
        ]
        if self.cookies_path and self.cookies_path.exists():
            command[1:1] = ["--cookies", str(self.cookies_path)]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise TranscriptError(self._build_download_error(completed.stderr or completed.stdout))

        vtt_path = self._find_vtt_path(work_dir, video_id)
        if vtt_path is None:
            raise TranscriptError("다운로드된 VTT 자막 파일을 찾지 못했습니다. 영상에 자막이 없을 수 있습니다.")

        return DownloadResult(metadata=metadata, vtt_path=vtt_path)

    def _resolve_yt_dlp(self) -> list[str]:
        executable = shutil.which("yt-dlp")
        if executable:
            return [executable]

        embedded_exe = Path(".venv") / "Scripts" / "yt-dlp.exe"
        if embedded_exe.exists():
            return [str(embedded_exe)]

        embedded_python = Path(".venv") / "Scripts" / "python.exe"
        if embedded_python.exists() and self._python_has_yt_dlp(embedded_python):
            return [str(embedded_python), "-m", "yt_dlp"]

        raise TranscriptError(
            "yt-dlp가 설치되어 있지 않습니다. `.venv\\Scripts\\python.exe -m pip install yt-dlp` 후 다시 시도해 주세요."
        )

    def _python_has_yt_dlp(self, python_executable: Path) -> bool:
        completed = subprocess.run(
            [str(python_executable), "-c", "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('yt_dlp') else 1)"],
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    def _fetch_metadata(self, yt_dlp: list[str], url: str, video_id: str) -> VideoMetadata:
        command = [*yt_dlp, "--dump-single-json", "--skip-download", url]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            return VideoMetadata(video_id=video_id, url=url, title=f"YouTube Video ({video_id})")

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return VideoMetadata(video_id=video_id, url=url, title=f"YouTube Video ({video_id})")

        return VideoMetadata(
            video_id=video_id,
            url=url,
            title=payload.get("title") or f"YouTube Video ({video_id})",
            channel_name=payload.get("channel") or payload.get("uploader"),
            language_code=self._infer_language(payload),
        )

    def _find_vtt_path(self, work_dir: Path, video_id: str) -> Path | None:
        matches = sorted(work_dir.glob(f"{video_id}*.vtt"))
        return matches[0] if matches else None

    def _build_download_error(self, stderr: str) -> str:
        lowered = stderr.lower()
        if "subtitles" in lowered and "not available" in lowered:
            return "이 영상에는 내려받을 수 있는 자막이 없습니다."
        if "video unavailable" in lowered:
            return "이 영상을 사용할 수 없습니다. 비공개 또는 지역 제한 영상일 수 있습니다."
        if "sign in" in lowered:
            if self.cookies_path and self.cookies_path.exists():
                return "쿠키를 사용했지만 로그인 세션이 만료되었거나 이 영상 접근 권한이 부족합니다."
            return "로그인이 필요한 영상입니다. cookies.txt를 연결하면 가져올 수 있을 수 있습니다."
        return f"yt-dlp로 자막을 다운로드하지 못했습니다: {stderr.strip()}"

    def _infer_language(self, payload: dict) -> str | None:
        subtitles = payload.get("subtitles") or {}
        automatic = payload.get("automatic_captions") or {}
        available = list(subtitles.keys()) + list(automatic.keys())
        for preferred in self.subtitle_languages:
            if preferred in available:
                return preferred
        return available[0] if available else None
