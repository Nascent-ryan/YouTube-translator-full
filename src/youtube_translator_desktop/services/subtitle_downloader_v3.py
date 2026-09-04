from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import urlopen

from youtube_translator_desktop.models import VideoMetadata

from .errors import TranscriptError
from .url_utils import extract_video_id


@dataclass(slots=True)
class DownloadResult:
    metadata: VideoMetadata
    vtt_path: Path
    related_vtt_paths: list[Path]


@dataclass(slots=True)
class SubtitleDownloader:
    subtitle_languages: tuple[str, ...] = ("ko", "en", "en-US", "en-GB")
    cookies_path: Path | None = None

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        video_id = extract_video_id(url)
        canonical_url = self._canonical_video_url(video_id)
        yt_dlp = self._resolve_yt_dlp()
        work_dir = output_dir / "downloads"
        work_dir.mkdir(parents=True, exist_ok=True)

        metadata = self._fetch_metadata(yt_dlp, canonical_url, video_id)
        output_template = str(work_dir / "%(id)s.%(ext)s")
        command = [
            *yt_dlp,
            "--ignore-no-formats-error",
            "--no-part",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs",
            ",".join(self.subtitle_languages),
            "--sub-format",
            "vtt",
            "--output",
            output_template,
        ]
        if self.cookies_path and self.cookies_path.exists():
            command.extend(["--cookies", str(self.cookies_path)])
        command.append(canonical_url)

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._clean_subprocess_env(),
        )
        related_paths = sorted(work_dir.glob(f"{video_id}*.vtt"))
        if completed.returncode != 0 and not related_paths:
            raise TranscriptError(self._build_download_error(completed.stderr or completed.stdout))

        selected_path = self._find_vtt_path(related_paths)
        if selected_path is None:
            diagnostic = completed.stderr.strip() or completed.stdout.strip()
            raise TranscriptError(self._build_missing_vtt_error(diagnostic))

        return DownloadResult(
            metadata=metadata,
            vtt_path=selected_path,
            related_vtt_paths=related_paths,
        )

    def _canonical_video_url(self, video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

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
            [
                str(python_executable),
                "-c",
                "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('yt_dlp') else 1)",
            ],
            capture_output=True,
            text=True,
            env=self._clean_subprocess_env(),
        )
        return completed.returncode == 0

    def _fetch_metadata(self, yt_dlp: list[str], url: str, video_id: str) -> VideoMetadata:
        command = [
            *yt_dlp,
            "--ignore-no-formats-error",
            "--dump-single-json",
            "--skip-download",
        ]
        if self.cookies_path and self.cookies_path.exists():
            command.extend(["--cookies", str(self.cookies_path)])
        command.append(url)

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._clean_subprocess_env(),
        )
        if completed.returncode != 0:
            return self._fetch_oembed_metadata(url, video_id)

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return self._fetch_oembed_metadata(url, video_id)

        return VideoMetadata(
            video_id=video_id,
            url=url,
            title=payload.get("title") or f"YouTube Video ({video_id})",
            channel_name=payload.get("channel") or payload.get("uploader"),
            language_code=self._infer_language(payload),
        )

    def _fetch_oembed_metadata(self, url: str, video_id: str) -> VideoMetadata:
        oembed_url = f"https://www.youtube.com/oembed?url={quote_plus(url)}&format=json"
        try:
            with urlopen(oembed_url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError):
            return VideoMetadata(video_id=video_id, url=url, title=f"YouTube Video ({video_id})")

        return VideoMetadata(
            video_id=video_id,
            url=url,
            title=payload.get("title") or f"YouTube Video ({video_id})",
            channel_name=payload.get("author_name"),
            language_code=None,
        )

    def _find_vtt_path(self, paths: list[Path]) -> Path | None:
        if not paths:
            return None

        markers = (".ko.", ".ko-", ".ko.vtt", ".en.", ".en-", ".en.vtt")
        for marker in markers:
            for path in paths:
                if marker in path.name:
                    return path
        return paths[0]

    def _build_download_error(self, stderr: str) -> str:
        lowered = stderr.lower()
        if "unable to connect to proxy" in lowered:
            return "시스템 프록시 설정 때문에 YouTube 연결에 실패했습니다."
        if "unable to rename file" in lowered:
            return "OneDrive 또는 Windows가 다운로드 파일 이름 변경을 막고 있습니다."
        if "subtitles" in lowered and "not available" in lowered:
            return "이 영상에는 내려받을 수 있는 자막이 없습니다."
        if "video unavailable" in lowered:
            return "이 영상을 사용할 수 없습니다. 비공개 또는 지역 제한 영상일 수 있습니다."
        if "requested format is not available" in lowered:
            if not self.cookies_path or not self.cookies_path.exists():
                return (
                    "YouTube 자막 요청이 제한됐고, 서버에서 쿠키 파일을 읽지 못하고 있습니다. "
                    "Render Secret File과 YTDLP_COOKIES_PATH 설정을 확인해 주세요."
                )
            return "자막은 받을 수 있지만 YouTube 응답 형식이 불안정합니다. 다시 시도해 주세요."
        if "sign in" in lowered:
            if self.cookies_path and self.cookies_path.exists():
                return "쿠키를 사용했지만 로그인 세션이 만료되었거나 이 영상 접근 권한이 부족합니다."
            return "로그인이 필요한 영상입니다. cookies.txt를 연결해 주세요."
        return f"yt-dlp로 자막을 다운로드하지 못했습니다: {stderr.strip()}"

    def _build_missing_vtt_error(self, diagnostic: str) -> str:
        """Keep yt-dlp's useful diagnosis when it exits without subtitle files."""
        if diagnostic:
            return self._build_download_error(diagnostic)
        return "다운로드된 VTT 자막 파일을 찾지 못했습니다. 자막 언어 또는 YouTube 접근 제한을 확인해 주세요."

    def _infer_language(self, payload: dict) -> str | None:
        subtitles = payload.get("subtitles") or {}
        automatic = payload.get("automatic_captions") or {}
        available = list(subtitles.keys()) + list(automatic.keys())
        for preferred in self.subtitle_languages:
            if preferred in available:
                return preferred
        return available[0] if available else None

    def _clean_subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            env.pop(key, None)
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"
        return env
