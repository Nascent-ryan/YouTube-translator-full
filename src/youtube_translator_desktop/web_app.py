from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from .config import AppConfig
from .services.errors import AppError
from .services.markdown_exporter_v2 import MarkdownExporter
from .services.original_markdown_builder import OriginalMarkdownBuilder
from .services.pipeline import GenerationPipeline
from .services.postprocessor_v2 import PostProcessor
from .services.subtitle_downloader_v3 import SubtitleDownloader
from .services.vtt_converter_v13 import VttConverter


class ConvertRequest(BaseModel):
    url: str


@dataclass(slots=True)
class WebState:
    pipeline: GenerationPipeline
    output_dir: Path


def build_web_pipeline(config: AppConfig) -> GenerationPipeline:
    return GenerationPipeline(
        subtitle_downloader=SubtitleDownloader(cookies_path=config.cookies_path),
        vtt_converter=VttConverter(),
        postprocessor=PostProcessor(),
        markdown_exporter=MarkdownExporter(),
        original_markdown_builder=OriginalMarkdownBuilder(),
    )


def create_app(config: AppConfig | None = None) -> FastAPI:
    loaded_config = config or AppConfig.load()
    app = FastAPI(title="YouTube Markdown Web", version="0.1.0")
    output_dir = loaded_config.default_output_dir / "web"
    app.state.web_state = WebState(
        pipeline=build_web_pipeline(loaded_config),
        output_dir=output_dir,
    )

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(_render_page())

    @app.get("/manifest.webmanifest")
    async def manifest() -> Response:
        return Response(_render_manifest(), media_type="application/manifest+json")

    @app.get("/sw.js")
    async def service_worker() -> Response:
        return Response(_render_service_worker(), media_type="application/javascript")

    @app.get("/icon.svg")
    async def icon() -> Response:
        return Response(_render_icon_svg(), media_type="image/svg+xml")

    @app.post("/api/convert")
    async def convert(request: ConvertRequest) -> dict[str, str | None]:
        state: WebState = app.state.web_state
        try:
            result = state.pipeline.run(request.url.strip(), state.output_dir)
        except AppError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        output_name = result.output_path.name
        return {
            "title": result.subtitle_document.metadata.title,
            "channel": result.subtitle_document.metadata.channel_name or "정보 없음",
            "markdown": result.markdown_text,
            "rendered_html": render_markdown_html(result.markdown_text),
            "download_url": f"/downloads/{output_name}",
            "output_name": output_name,
            "original_download_url": f"/downloads/{result.original_output_path.name}" if result.original_output_path else None,
            "original_output_name": result.original_output_path.name if result.original_output_path else None,
        }

    @app.get("/downloads/{filename}")
    async def download_file(filename: str) -> FileResponse:
        safe_name = Path(filename).name
        file_path = app.state.web_state.output_dir / safe_name
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        return FileResponse(file_path, media_type="text/markdown; charset=utf-8", filename=safe_name)

    return app


def render_markdown_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_parts: list[str] = []
    in_list = False
    in_plain = False
    plain_buffer: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def close_plain() -> None:
        nonlocal in_plain, plain_buffer
        if in_plain:
            html_parts.append('<div class="plain-text">')
            html_parts.extend(f"<p>{escape(line)}</p>" for line in plain_buffer if line.strip())
            html_parts.append("</div>")
            in_plain = False
            plain_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            close_list()
            if not in_plain:
                continue
            plain_buffer.append("")
            continue

        if line.startswith("# "):
            close_list()
            close_plain()
            html_parts.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            close_list()
            close_plain()
            title = line[3:]
            css_class = "plain-title" if title == "전체 번역 텍스트" else ""
            class_attr = f' class="{css_class}"' if css_class else ""
            html_parts.append(f"<h2{class_attr}>{escape(title)}</h2>")
            if title == "전체 번역 텍스트":
                in_plain = True
            continue
        if line.startswith("### "):
            close_list()
            close_plain()
            html_parts.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("**") and line.endswith("**"):
            close_list()
            close_plain()
            html_parts.append(f'<div class="speaker">{escape(line.strip("*"))}</div>')
            continue
        if line.startswith("- "):
            close_plain()
            if not in_list:
                html_parts.append('<ul class="bullet-list">')
                in_list = True
            html_parts.append(f"<li>{escape(line[2:])}</li>")
            continue

        close_list()
        if in_plain:
            plain_buffer.append(line)
        else:
            close_plain()
            html_parts.append(f"<p>{escape(line)}</p>")

    close_list()
    close_plain()
    return "\n".join(html_parts)


def _render_page() -> str:
    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Translator (Full version)</title>
  <meta name="theme-color" content="#b14d2f">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="YT Translator">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/icon.svg">
  <style>
    :root {
      --bg: #f5efe3;
      --panel: #fffaf2;
      --ink: #1f1b16;
      --muted: #6a6258;
      --line: #d9ccba;
      --accent: #b14d2f;
      --accent-dark: #7f311b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Apple SD Gothic Neo", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7d8 0, transparent 28%),
        linear-gradient(180deg, #f7f1e6 0%, #efe6d8 100%);
    }
    .page {
      max-width: 900px;
      margin: 0 auto;
      padding: 24px 16px 56px;
    }
    .hero, .panel, .result-card {
      background: rgba(255, 250, 242, 0.92);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 12px 30px rgba(70, 49, 25, 0.08);
    }
    .hero {
      padding: 24px;
      margin-bottom: 16px;
    }
    .eyebrow {
      margin: 0 0 8px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
    }
    h1 {
      margin: 0;
      font-size: clamp(22px, 4vw, 26px);
      line-height: 1.18;
      letter-spacing: -0.02em;
    }
    .hero p {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: 14px;
    }
    .panel {
      padding: 18px;
      margin-bottom: 16px;
    }
    label {
      display: block;
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .input-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    input[type="url"] {
      width: 100%;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: white;
      font-size: 16px;
    }
    button {
      border: 0;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent-dark));
      color: white;
      padding: 14px 18px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: progress;
    }
    .status {
      margin-top: 12px;
      min-height: 22px;
      font-size: 14px;
      color: var(--muted);
    }
    .status.error { color: #9e2d24; }
    .status.success { color: #296b31; }
    .result-card {
      display: none;
      padding: 20px;
    }
    .result-card.visible { display: block; }
    .result-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 12px;
    }
    .download-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--accent-dark);
      font-weight: 700;
      text-decoration: none;
      margin-bottom: 18px;
    }
    .rendered {
      border-top: 1px solid var(--line);
      padding-top: 18px;
    }
    .rendered h1, .rendered h2, .rendered h3 {
      margin-top: 0;
    }
    .rendered h2 {
      margin-top: 24px;
      font-size: 18px;
    }
    .rendered h3 {
      margin-top: 20px;
      font-size: 18px;
      color: var(--accent-dark);
    }
    .rendered h2:first-of-type {
      font-size: 15px;
      color: var(--muted);
      letter-spacing: 0.02em;
    }
    .rendered h2:first-of-type + .bullet-list,
    .rendered h2:first-of-type + p {
      font-size: 13px;
      color: var(--muted);
    }
    .rendered h2:first-of-type + .bullet-list li {
      margin: 6px 0;
      line-height: 1.5;
    }
    .speaker {
      margin-top: 14px;
      font-weight: 700;
      color: var(--accent-dark);
    }
    .bullet-list {
      margin: 10px 0 0 0;
      padding-left: 20px;
    }
    .bullet-list li {
      margin: 8px 0;
      line-height: 1.7;
    }
    .plain-text {
      padding: 14px;
      border-radius: 16px;
      background: #f8f2e7;
    }
    .plain-text p {
      margin: 10px 0;
      white-space: pre-wrap;
      line-height: 1.7;
    }
    .raw-block {
      margin-top: 18px;
    }
    details {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
      background: #fbf7f0;
    }
    summary {
      cursor: pointer;
      font-weight: 700;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 12px 0 0;
      font-size: 13px;
      line-height: 1.55;
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Mobile Ready</p>
      <h1>YouTube Translator (Full version)</h1>
      <p>YouTube 링크를 붙여 넣으면 자막을 가져와 한국어 정리본을 보기 좋게 보여주고, Markdown 파일도 함께 내려받을 수 있습니다.</p>
    </section>

    <section class="panel">
      <label for="youtube-url">YouTube 링크</label>
      <div class="input-row">
        <input id="youtube-url" type="url" placeholder="https://www.youtube.com/watch?v=..." />
        <button id="submit-button" type="button">정리 시작</button>
      </div>
      <div id="status" class="status"></div>
    </section>

    <section id="result-card" class="result-card">
      <div id="result-meta" class="result-meta"></div>
      <a id="download-link" class="download-link" href="#" hidden>한글 정리본 다운로드</a>
      <a id="original-download-link" class="download-link" href="#" hidden>영어 원문 다운로드</a>
      <article id="rendered" class="rendered"></article>
      <div class="raw-block">
        <details>
          <summary>원본 Markdown 보기</summary>
          <pre id="raw-markdown"></pre>
        </details>
      </div>
    </section>
  </main>

  <script>
    const urlInput = document.getElementById("youtube-url");
    const submitButton = document.getElementById("submit-button");
    const statusNode = document.getElementById("status");
    const resultCard = document.getElementById("result-card");
    const renderedNode = document.getElementById("rendered");
    const rawMarkdownNode = document.getElementById("raw-markdown");
    const metaNode = document.getElementById("result-meta");
    const downloadLink = document.getElementById("download-link");
    const originalDownloadLink = document.getElementById("original-download-link");

    async function convert() {
      const url = urlInput.value.trim();
      if (!url) {
        statusNode.textContent = "링크를 먼저 입력해 주세요.";
        statusNode.className = "status error";
        return;
      }

      submitButton.disabled = true;
      statusNode.textContent = "자막을 가져오고 정리 중입니다. 잠시만 기다려 주세요.";
      statusNode.className = "status";
      resultCard.classList.remove("visible");
      originalDownloadLink.hidden = true;

      try {
        const response = await fetch("/api/convert", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "변환에 실패했습니다.");
        }

        renderedNode.innerHTML = payload.rendered_html;
        rawMarkdownNode.textContent = payload.markdown;
        metaNode.innerHTML = `
          <span>제목: ${payload.title}</span>
          <span>채널: ${payload.channel}</span>
          <span>파일: ${payload.output_name}</span>
        `;
        downloadLink.href = payload.download_url;
        downloadLink.hidden = false;
        if (payload.original_download_url) {
          originalDownloadLink.href = payload.original_download_url;
          originalDownloadLink.hidden = false;
        } else {
          originalDownloadLink.hidden = true;
        }
        resultCard.classList.add("visible");
        statusNode.textContent = "변환이 완료되었습니다.";
        statusNode.className = "status success";
      } catch (error) {
        statusNode.textContent = error.message || "변환 중 오류가 발생했습니다.";
        statusNode.className = "status error";
      } finally {
        submitButton.disabled = false;
      }
    }

    submitButton.addEventListener("click", convert);
    urlInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        convert();
      }
    });

    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
      });
    }
  </script>
</body>
</html>
"""


def _render_manifest() -> str:
    return """{
  "name": "YouTube Translator (Full version)",
  "short_name": "YT Translator",
  "description": "YouTube 링크를 붙여 넣으면 자막을 정리된 Markdown과 읽기 좋은 한국어 번역 본문으로 보여주는 앱",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#f5efe3",
  "theme_color": "#b14d2f",
  "lang": "ko",
  "icons": [
    {
      "src": "/icon.svg",
      "sizes": "any",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    }
  ]
}"""


def _render_service_worker() -> str:
    return """const CACHE_NAME = "youtube-translator-v1";
const APP_SHELL = ["/", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/downloads/")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }

      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type !== "basic") {
          return response;
        }

        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseToCache));
        return response;
      });
    })
  );
});"""


def _render_icon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="56" fill="#b14d2f"/>
  <rect x="36" y="48" width="184" height="160" rx="28" fill="#fff7ed"/>
  <path d="M107 92h42c20 0 33 14 33 31s-13 31-33 31h-18v26h-24V92zm24 22v18h18c6 0 10-4 10-9s-4-9-10-9h-18z" fill="#7f311b"/>
  <path d="M84 111l28 17-28 17z" fill="#b14d2f"/>
</svg>"""
