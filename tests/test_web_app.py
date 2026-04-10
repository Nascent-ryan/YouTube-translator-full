from youtube_translator_desktop.web_app import render_markdown_html


def test_render_markdown_html_formats_sections_and_lists() -> None:
    markdown_text = """# 샘플 제목

## 영상 정보
- 링크: https://example.com

## 전체 정리
### 주제 1. CPU / GPU
**진행자**
- 왜 병목이 커지는지 질문함
**게스트**
- 2026년에는 CPU와 GPU 병목이 동시에 커질 수 있다고 설명함

## 전체 번역 텍스트
첫 문장
둘째 문장
"""

    html = render_markdown_html(markdown_text)

    assert "<h1>샘플 제목</h1>" in html
    assert '<ul class="bullet-list">' in html
    assert '<div class="speaker">진행자</div>' in html
    assert '<h3>주제 1. CPU / GPU</h3>' in html
    assert '<div class="plain-text">' in html
    assert "첫 문장" in html
