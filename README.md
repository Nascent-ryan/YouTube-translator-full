# YouTube 번역 정리 데스크톱 앱

YouTube 링크를 입력하면 자막을 가져와 한국어 중심의 정리를 생성하고 Markdown으로 저장하는 PySide6 데스크톱 앱입니다.

## 기능

- YouTube URL 1차 검증
- YouTube 자막 우선 수집
- OpenAI API 기반 한국어 정리 생성
- 긴 자막 chunk 분할 처리
- 앱 화면 미리보기 + Markdown 파일 저장
- `.env` 기반 API 키 / 기본 저장 경로 설정

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
```

`.env`에 `OPENAI_API_KEY`를 채워 주세요.

## 실행

```bash
python -m youtube_translator_desktop
```

## 테스트

```bash
pytest
```

## 프로젝트 구조

```text
src/youtube_translator_desktop/
  app.py
  config.py
  models.py
  services/
  ui/
```

## 현재 범위

- v1은 자막 우선만 지원합니다.
- 자막이 없거나 너무 짧으면 앱이 실패 사유를 표시합니다.
- STT fallback은 후속 버전에서 확장할 수 있도록 인터페이스만 분리해 두었습니다.
