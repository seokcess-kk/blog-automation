"""
analyzer 모듈 테스트.

pytest 실행: pytest tests/test_analyzer.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSerpCollector:
    """serp_collector 모듈 테스트."""

    def test_collect_top_urls_returns_list(self):
        """collect_top_urls가 리스트를 반환하는지 테스트."""
        from src.analyzer.serp_collector import collect_top_urls

        # API가 없어도 빈 리스트를 반환해야 함
        with patch("src.analyzer.serp_collector.search_blog") as mock_search:
            mock_search.return_value = []
            result = collect_top_urls("테스트 키워드", use_fallback=False)

            assert isinstance(result, list)

    def test_collect_top_urls_filters_naver_blog(self):
        """네이버 블로그 URL만 필터링하는지 테스트."""
        from src.analyzer.serp_collector import collect_top_urls

        mock_results = [
            {"link": "https://blog.naver.com/test1/123"},
            {"link": "https://example.com/not-a-blog"},
            {"link": "https://blog.naver.com/test2/456"},
        ]

        with patch("src.analyzer.serp_collector.search_blog") as mock_search:
            mock_search.return_value = mock_results
            result = collect_top_urls("테스트", use_fallback=False)

            assert len(result) == 2
            assert all("blog.naver.com" in url for url in result)

    def test_validate_url(self):
        """URL 유효성 검사 테스트."""
        from src.analyzer.serp_collector import validate_url

        assert validate_url("https://blog.naver.com/test/123") is True
        assert validate_url("https://m.blog.naver.com/test/123") is True
        assert validate_url("https://example.com") is False
        assert validate_url("") is False
        assert validate_url(None) is False


class TestContentParser:
    """content_parser 모듈 테스트."""

    def test_parsed_content_output_schema(self):
        """ParsedContent 출력 스키마 테스트."""
        from src.analyzer.content_parser import ParsedContent, ContentSection, content_to_dict

        sections = [
            ContentSection(
                heading="소제목1", heading_tag="h2", text="텍스트",
                char_count=3, image_count=1, image_contexts=["컨텍스트"], order_index=0,
            ),
        ]

        content = ParsedContent(
            url="https://blog.naver.com/test/123",
            title="테스트 제목",
            char_count=1500,
            image_count=5,
            heading_count=3,
            headings=["소제목1", "소제목2", "소제목3"],
            keyword_in_title=True,
            keyword_positions=[10, 100, 500],
            image_positions=[0.1, 0.3, 0.5, 0.7, 0.9],
            has_list=True,
            has_table=False,
            related_keywords=["연관1", "연관2"],
            sections=sections,
            full_text="전체 텍스트 내용" * 100,
        )

        result = content_to_dict(content)

        # 필수 필드 확인
        assert "url" in result
        assert "title" in result
        assert "char_count" in result
        assert "image_count" in result
        assert "heading_count" in result
        assert "headings" in result
        assert "keyword_in_title" in result
        assert "keyword_positions" in result
        assert "image_positions" in result
        assert "has_list" in result
        assert "has_table" in result
        assert "related_keywords" in result

        # 새로 추가된 필드 확인
        assert "sections" in result
        assert "full_text" in result
        assert len(result["sections"]) == 1
        assert result["sections"][0]["heading"] == "소제목1"
        assert result["sections"][0]["heading_tag"] == "h2"

        # 타입 확인
        assert isinstance(result["char_count"], int)
        assert isinstance(result["image_count"], int)
        assert isinstance(result["headings"], list)
        assert isinstance(result["keyword_in_title"], bool)

    def test_content_to_dict_conversion(self):
        """ParsedContent → dict 변환 테스트."""
        from src.analyzer.content_parser import ParsedContent, content_to_dict

        content = ParsedContent(
            url="https://example.com",
            title="Test",
            char_count=100,
            image_count=2,
            heading_count=1,
            headings=["H1"],
            keyword_in_title=False,
            keyword_positions=[],
            image_positions=[0.5],
            has_list=False,
            has_table=False,
            related_keywords=[],
        )

        result = content_to_dict(content)

        assert result["url"] == "https://example.com"
        assert result["title"] == "Test"
        assert result["char_count"] == 100
        # sections/full_text는 비어있으면 포함되지 않음
        assert "sections" not in result
        assert "full_text" not in result


class TestPatternExtractor:
    """pattern_extractor 모듈 테스트."""

    def test_extract_patterns_calculates_averages(self):
        """평균 계산 테스트."""
        from src.analyzer.pattern_extractor import extract_patterns, pattern_to_dict
        from src.analyzer.content_parser import ParsedContent

        contents = [
            ParsedContent(
                url="url1", title="제목1", char_count=1000,
                image_count=4, heading_count=2, headings=[],
                keyword_in_title=True, keyword_positions=[],
                image_positions=[], has_list=False, has_table=False,
                related_keywords=["키워드A"],
            ),
            ParsedContent(
                url="url2", title="제목2", char_count=2000,
                image_count=6, heading_count=4, headings=[],
                keyword_in_title=True, keyword_positions=[],
                image_positions=[], has_list=False, has_table=False,
                related_keywords=["키워드A", "키워드B"],
            ),
            ParsedContent(
                url="url3", title="제목3", char_count=1500,
                image_count=5, heading_count=3, headings=[],
                keyword_in_title=False, keyword_positions=[],
                image_positions=[], has_list=False, has_table=False,
                related_keywords=["키워드A"],
            ),
        ]

        pattern = extract_patterns(contents, "테스트")

        assert pattern is not None
        assert pattern.avg_char_count == 1500  # (1000+2000+1500)/3
        assert pattern.avg_image_count == 5  # (4+6+5)/3
        assert pattern.avg_heading_count == 3  # (2+4+3)/3

    def test_extract_patterns_finds_common_keywords(self):
        """공통 키워드 추출 테스트."""
        from src.analyzer.pattern_extractor import extract_patterns
        from src.analyzer.content_parser import ParsedContent

        contents = [
            ParsedContent(
                url="url1", title="", char_count=1000,
                image_count=0, heading_count=0, headings=[],
                keyword_in_title=False, keyword_positions=[],
                image_positions=[], has_list=False, has_table=False,
                related_keywords=["공통", "개별1"],
            ),
            ParsedContent(
                url="url2", title="", char_count=1000,
                image_count=0, heading_count=0, headings=[],
                keyword_in_title=False, keyword_positions=[],
                image_positions=[], has_list=False, has_table=False,
                related_keywords=["공통", "개별2"],
            ),
        ]

        pattern = extract_patterns(contents, "테스트")

        assert pattern is not None
        assert "공통" in pattern.related_keywords

    def test_pattern_to_dict_conversion(self):
        """ExtractedPattern → dict 변환 테스트."""
        from src.analyzer.pattern_extractor import ExtractedPattern, pattern_to_dict

        pattern = ExtractedPattern(
            avg_char_count=1500,
            avg_image_count=5,
            avg_heading_count=3,
            title_patterns=["keyword_position:front"],
            keyword_placement={"in_title_ratio": 0.8},
            related_keywords=["연관1", "연관2"],
            content_structure={"has_list_ratio": 0.5},
            image_position_pattern={"pattern": "distributed"},
            source_count=5,
            source_urls=["url1", "url2"],
            source_titles=["제목1", "제목2"],
        )

        result = pattern_to_dict(pattern)

        assert result["avg_char_count"] == 1500
        assert result["avg_image_count"] == 5
        assert result["source_count"] == 5
        assert isinstance(result["title_patterns"], list)
        assert result["source_titles"] == ["제목1", "제목2"]


class TestAnalyzeKeyword:
    """analyze_keyword 통합 테스트."""

    def test_analyze_keyword_returns_correct_structure(self):
        """analyze_keyword 반환 구조 테스트."""
        from src.analyzer import analyze_keyword

        with patch("src.analyzer.collect_top_urls") as mock_collect:
            mock_collect.return_value = []

            result = analyze_keyword("테스트", top_n=5)

            # 기본 구조 확인
            assert "success" in result
            assert "keyword" in result
            assert "error" in result

            # URL 없으면 실패
            assert result["success"] is False

    @pytest.mark.live
    def test_analyze_keyword_live(self):
        """실제 API 호출 테스트 (--live 옵션으로 실행)."""
        from src.analyzer import analyze_keyword

        result = analyze_keyword("맛집 추천", top_n=3)

        if result["success"]:
            assert "pattern" in result
            assert result["pattern"] is not None
            assert "avg_char_count" in result["pattern"]
