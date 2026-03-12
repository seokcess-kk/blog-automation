"""
deep_analyzer 모듈 테스트.

pytest 실행: pytest tests/test_deep_analyzer.py -v
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import field

from src.analyzer.content_parser import ParsedContent, ContentSection


def _make_sections() -> list[ContentSection]:
    """테스트용 섹션 목록을 생성합니다."""
    return [
        ContentSection(
            heading="",
            heading_tag="",
            text="안녕하세요 오늘은 다이어트에 대해 이야기해볼게요.",
            char_count=25,
            image_count=1,
            image_contexts=["안녕하세요 오늘은"],
            order_index=0,
        ),
        ContentSection(
            heading="다이어트 방법",
            heading_tag="h2",
            text="효과적인 다이어트 방법은 여러 가지가 있습니다. 식단 조절과 운동이 핵심입니다.",
            char_count=40,
            image_count=2,
            image_contexts=["효과적인 다이어트", "식단 조절과 운동"],
            order_index=1,
        ),
        ContentSection(
            heading="마무리",
            heading_tag="h2",
            text="꾸준히 실천하는 것이 가장 중요합니다.",
            char_count=18,
            image_count=0,
            image_contexts=[],
            order_index=2,
        ),
    ]


def _make_parsed_content(
    url: str = "https://blog.naver.com/test/123",
    title: str = "다이어트 방법 총정리",
    with_sections: bool = True,
) -> ParsedContent:
    """테스트용 ParsedContent를 생성합니다."""
    sections = _make_sections() if with_sections else []
    return ParsedContent(
        url=url,
        title=title,
        char_count=2000,
        image_count=5,
        heading_count=3,
        headings=["다이어트 방법", "식단 관리", "마무리"],
        keyword_in_title=True,
        keyword_positions=[0, 100, 500],
        image_positions=[0.1, 0.3, 0.5, 0.7, 0.9],
        has_list=True,
        has_table=False,
        related_keywords=["식단", "운동", "건강"],
        raw_text="안녕하세요 다이어트 방법...",
        sections=sections,
        full_text="안녕하세요 다이어트 방법에 대해 이야기해볼게요. " * 50,
    )


class TestExtractSections:
    """_extract_sections 함수 테스트."""

    def test_extract_sections_se_editor_mock(self):
        """SE 에디터 DOM에서 섹션 추출 테스트."""
        from src.analyzer.content_parser import _extract_sections

        # Mock SE editor container
        container = MagicMock()

        # se-component 요소들
        comp_title = MagicMock()
        comp_title.attrib = {"class": "se-component se-documentTitle"}

        comp_text1 = MagicMock()
        comp_text1.attrib = {"class": "se-component se-text"}
        comp_text1.css.side_effect = lambda sel: {
            "h2": [],
            "h3": [],
            "strong, b": [],
        }.get(sel, [])
        comp_text1.get_all_text.return_value = "도입부 텍스트입니다."

        comp_image = MagicMock()
        comp_image.attrib = {"class": "se-component se-image"}
        img_elem = MagicMock()
        img_elem.attrib = {"src": "https://blogfiles.naver.net/test.jpg"}
        comp_image.css.return_value = [img_elem]

        comp_text2 = MagicMock()
        comp_text2.attrib = {"class": "se-component se-text"}
        h2_elem = MagicMock()
        h2_elem.text = "소제목 테스트"
        comp_text2.css.side_effect = lambda sel: {
            "h2": [h2_elem],
            "h3": [],
            "strong, b": [],
        }.get(sel, [])
        comp_text2.get_all_text.return_value = "소제목 아래 본문 내용입니다."

        container.css.side_effect = lambda sel: {
            ".se-component": [comp_title, comp_text1, comp_image, comp_text2],
        }.get(sel, [])

        sections = _extract_sections(container)

        # 도입부 + 소제목 섹션 = 2개
        assert len(sections) == 2
        # 첫 번째 섹션: 도입부 (heading 없음, 이미지 1개 포함)
        assert sections[0].heading == ""
        assert sections[0].heading_tag == ""
        assert sections[0].order_index == 0
        assert "도입부" in sections[0].text
        assert sections[0].image_count == 1
        # 두 번째 섹션: h2 소제목
        assert sections[1].heading == "소제목 테스트"
        assert sections[1].heading_tag == "h2"
        assert sections[1].order_index == 1
        assert "소제목 아래" in sections[1].text

    def test_content_section_dataclass(self):
        """ContentSection 데이터클래스 생성 테스트."""
        section = ContentSection(
            heading="테스트 소제목",
            heading_tag="h2",
            text="본문 텍스트입니다.",
            char_count=9,
            image_count=1,
            image_contexts=["전후 텍스트"],
            order_index=0,
        )

        assert section.heading == "테스트 소제목"
        assert section.heading_tag == "h2"
        assert section.char_count == 9
        assert section.image_count == 1
        assert len(section.image_contexts) == 1


class TestAnalyzeBlogDeep:
    """analyze_blog_deep 함수 테스트."""

    def test_analyze_blog_deep_success(self):
        """단일 블로그 심층 분석 성공 테스트 (Claude mock)."""
        from src.analyzer.deep_analyzer import analyze_blog_deep

        mock_response = {
            "writing_tone": "대화체",
            "sentence_style": "짧은 문장 위주",
            "opening_strategy": "경험담",
            "closing_strategy": "CTA",
            "section_flow": [
                {"heading": "도입", "role": "도입", "char_ratio": 0.2},
            ],
            "content_type": "리뷰형",
            "image_placement": [
                {"position": "h2 직후", "purpose": "시각적 도입", "count": 1},
            ],
            "keyword_usage_style": "자연스러운 대화체에 녹임",
            "key_phrases": ["효과적인 방법", "직접 해봤는데"],
        }

        content = _make_parsed_content()

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.return_value = mock_response

            result = analyze_blog_deep(content, "다이어트")

            assert result is not None
            assert result.writing_tone == "대화체"
            assert result.content_type == "리뷰형"
            assert result.opening_strategy == "경험담"
            assert len(result.key_phrases) == 2

    def test_analyze_blog_deep_no_sections(self):
        """섹션 없는 콘텐츠 분석 테스트."""
        from src.analyzer.deep_analyzer import analyze_blog_deep

        content = _make_parsed_content(with_sections=False)
        content.full_text = ""  # full_text도 비움

        result = analyze_blog_deep(content, "다이어트")

        assert result is None

    def test_analyze_blog_deep_full_text_fallback(self):
        """섹션 없지만 full_text 있을 때 fallback 프롬프트 테스트."""
        from src.analyzer.deep_analyzer import analyze_blog_deep, _build_single_blog_prompt

        content = _make_parsed_content(with_sections=False)
        # full_text는 있음

        # 프롬프트에 full_text 내용이 포함되는지 확인
        prompt = _build_single_blog_prompt(content, "다이어트")
        assert "[전체 본문]" in prompt
        assert "다이어트" in prompt

        # Claude mock으로 분석 성공 확인
        mock_response = {
            "writing_tone": "정보형",
            "sentence_style": "설명 위주",
            "opening_strategy": "팩트 제시",
            "closing_strategy": "요약",
            "section_flow": [],
            "content_type": "정보형",
            "image_placement": [],
            "keyword_usage_style": "객관적",
            "key_phrases": [],
        }

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.return_value = mock_response
            result = analyze_blog_deep(content, "다이어트")
            assert result is not None
            assert result.writing_tone == "정보형"

    def test_analyze_blog_deep_claude_failure(self):
        """Claude API 실패 시 None 반환 테스트."""
        from src.analyzer.deep_analyzer import analyze_blog_deep

        content = _make_parsed_content()

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.return_value = None

            result = analyze_blog_deep(content, "다이어트")

            assert result is None


class TestAnalyzeBlogsDeep:
    """analyze_blogs_deep 종합 분석 테스트."""

    def test_analyze_blogs_deep_success(self):
        """종합 심층 분석 성공 테스트."""
        from src.analyzer.deep_analyzer import analyze_blogs_deep

        contents = [
            _make_parsed_content(url=f"https://blog.naver.com/test/{i}", title=f"테스트 블로그 {i}")
            for i in range(3)
        ]

        single_response = {
            "writing_tone": "대화체",
            "sentence_style": "짧은 문장 위주",
            "opening_strategy": "경험담",
            "closing_strategy": "CTA",
            "section_flow": [],
            "content_type": "리뷰형",
            "image_placement": [],
            "keyword_usage_style": "자연스럽게 배치",
            "key_phrases": ["좋은 표현"],
        }

        agg_response = {
            "dominant_tone": "대화체",
            "common_structure": "도입→정보→비교→CTA",
            "image_strategy": "H2 직후 1개씩 배치",
            "recommended_sections": [
                {"heading": "도입", "target_chars": 300, "image_count": 1, "role": "도입", "guidelines": "경험담"},
            ],
            "writing_guidelines": "친근한 대화체로 작성",
        }

        call_count = 0

        def mock_gemini_side_effect(prompt):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return single_response
            return agg_response

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.side_effect = mock_gemini_side_effect

            result = analyze_blogs_deep(contents, "다이어트", delay_seconds=0)

            assert result is not None
            assert result.dominant_tone == "대화체"
            assert result.common_structure == "도입→정보→비교→CTA"
            assert len(result.source_analyses) == 3
            assert len(result.recommended_sections) == 1

    def test_analyze_blogs_deep_empty_contents(self):
        """빈 콘텐츠 목록 테스트."""
        from src.analyzer.deep_analyzer import analyze_blogs_deep

        result = analyze_blogs_deep([], "다이어트")

        assert result is None

    def test_analyze_blogs_deep_all_failures(self):
        """모든 개별 분석 실패 시 None 반환 테스트."""
        from src.analyzer.deep_analyzer import analyze_blogs_deep

        contents = [_make_parsed_content()]

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.return_value = None

            result = analyze_blogs_deep(contents, "다이어트", delay_seconds=0)

            assert result is None

    def test_analyze_blogs_deep_aggregation_failure_fallback(self):
        """종합 분석 실패 시 개별 결과로 fallback 테스트."""
        from src.analyzer.deep_analyzer import analyze_blogs_deep

        contents = [_make_parsed_content()]

        single_response = {
            "writing_tone": "정보형",
            "sentence_style": "설명 위주",
            "opening_strategy": "팩트 제시",
            "closing_strategy": "요약",
            "section_flow": [],
            "content_type": "정보형",
            "image_placement": [],
            "keyword_usage_style": "객관적 배치",
            "key_phrases": [],
        }

        call_count = 0

        def mock_side_effect(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return single_response
            return None  # 종합 분석 실패

        with patch("src.analyzer.deep_analyzer._call_claude") as mock_gemini:
            mock_gemini.side_effect = mock_side_effect

            result = analyze_blogs_deep(contents, "다이어트", delay_seconds=0)

            assert result is not None
            assert result.dominant_tone == "정보형"
            assert result.common_structure == "개별 분석 참조"
            assert len(result.source_analyses) == 1


class TestDeepAnalysisToDict:
    """deep_analysis_to_dict 변환 테스트."""

    def test_to_dict_conversion(self):
        """AggregatedDeepAnalysis → dict 변환 테스트."""
        from src.analyzer.deep_analyzer import (
            AggregatedDeepAnalysis,
            BlogDeepAnalysis,
            deep_analysis_to_dict,
        )

        analysis = AggregatedDeepAnalysis(
            dominant_tone="대화체",
            common_structure="도입→본론→결론",
            image_strategy="H2 직후 배치",
            recommended_sections=[
                {"heading": "도입", "target_chars": 300, "image_count": 1, "role": "도입", "guidelines": "경험담"},
            ],
            writing_guidelines="친근한 톤 유지",
            source_analyses=[
                BlogDeepAnalysis(
                    url="https://blog.naver.com/test/1",
                    title="테스트 블로그",
                    writing_tone="대화체",
                    sentence_style="짧은 문장",
                    opening_strategy="경험담",
                    closing_strategy="CTA",
                    section_flow=[],
                    content_type="리뷰형",
                    image_placement=[],
                    keyword_usage_style="자연스럽게",
                    key_phrases=["좋은 표현"],
                ),
            ],
        )

        result = deep_analysis_to_dict(analysis)

        assert result["dominant_tone"] == "대화체"
        assert result["common_structure"] == "도입→본론→결론"
        assert result["image_strategy"] == "H2 직후 배치"
        assert len(result["recommended_sections"]) == 1
        assert len(result["source_analyses"]) == 1
        assert result["source_analyses"][0]["writing_tone"] == "대화체"
