from __future__ import annotations

from dataclasses import dataclass

from youtube_translator_desktop.models import SubtitleDocument

from .subtitle_downloader_v3 import DownloadResult
from .vtt_converter_v5 import TopicBlock, VttConverter as BaseVttConverter


@dataclass(slots=True)
class TopicSection:
    title: str
    paragraphs: list[str]


@dataclass(slots=True)
class VttConverter(BaseVttConverter):
    def convert(self, download_result: DownloadResult) -> SubtitleDocument:
        translated_segments = self.merge_segments(
            self.parse_segments(download_result.vtt_path.read_text(encoding="utf-8"))
        )
        turns = self._build_turns(translated_segments, [])
        topic_blocks = self._group_topics(turns)
        topic_sections = self._build_topic_sections(topic_blocks)
        plain_text = "\n".join(turn.text for turn in turns)
        markdown_text = self.render_markdown(download_result, topic_sections)

        return SubtitleDocument(
            metadata=download_result.metadata,
            vtt_path=download_result.vtt_path,
            markdown_text=markdown_text,
            plain_text=plain_text,
            segment_count=len(turns),
        )

    def render_markdown(
        self,
        download_result: DownloadResult,
        topic_sections: list[TopicSection],
    ) -> str:
        metadata = download_result.metadata
        title = metadata.title or f"YouTube Video ({metadata.video_id})"
        topic_body = "\n\n".join(
            self._render_topic_section(section, index + 1)
            for index, section in enumerate(topic_sections)
        )

        return f"""# {title}

## 영상 정보
- 링크: {metadata.url}
- 영상 ID: {metadata.video_id}
- 채널명: {metadata.channel_name or "정보 없음"}
- 출력 기준: 한국어 번역 문단 정리
- 사용 자막 파일: {download_result.vtt_path.name}
- 문단 수: {sum(len(section.paragraphs) for section in topic_sections)}

## 주제별 정리
{topic_body}
"""

    def _render_topic_section(self, section: TopicSection, index: int) -> str:
        lines = [f"### 주제 {index}. {section.title}"]
        lines.extend(section.paragraphs)
        return "\n\n".join(lines)

    def _build_topic_sections(self, topic_blocks: list[TopicBlock]) -> list[TopicSection]:
        sections: list[TopicSection] = []
        for block in topic_blocks:
            paragraphs = self._group_paragraphs(block)
            sections.append(TopicSection(title=block.title, paragraphs=paragraphs))
        return sections

    def _group_topics(self, turns):
        if not turns:
            return []

        blocks: list[TopicBlock] = []
        current_turns = [turns[0]]

        for turn in turns[1:]:
            recent_text = " ".join(item.text for item in current_turns[-2:])
            recent_keywords = self._keywords(recent_text)
            turn_keywords = self._keywords(turn.text)
            similarity = self._similarity(recent_keywords, turn_keywords)
            should_split = similarity < 0.14 and len(current_turns) >= 3

            if should_split:
                blocks.append(TopicBlock(title=self._make_topic_title(current_turns), turns=current_turns))
                current_turns = [turn]
            else:
                current_turns.append(turn)

        blocks.append(TopicBlock(title=self._make_topic_title(current_turns), turns=current_turns))
        return blocks

    def _group_paragraphs(self, block: TopicBlock) -> list[str]:
        if not block.turns:
            return []

        paragraphs: list[str] = []
        current_sentences: list[str] = [block.turns[0].text]
        current_keywords = self._keywords(block.turns[0].text)

        for turn in block.turns[1:]:
            turn_keywords = self._keywords(turn.text)
            similarity = self._similarity(current_keywords, turn_keywords)
            paragraph_is_large = len(current_sentences) >= 3
            content_shift = similarity < 0.22 and len(current_sentences) >= 2

            if paragraph_is_large or content_shift:
                paragraphs.append(" ".join(current_sentences).strip())
                current_sentences = [turn.text]
                current_keywords = turn_keywords
            else:
                current_sentences.append(turn.text)
                current_keywords |= turn_keywords

        if current_sentences:
            paragraphs.append(" ".join(current_sentences).strip())

        return paragraphs
