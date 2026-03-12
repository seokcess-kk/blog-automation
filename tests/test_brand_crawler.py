"""
brand_crawler 모듈 테스트.

pytest 실행: pytest tests/test_brand_crawler.py -v
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.analyzer.brand_crawler import (
    crawl_brand_homepage,
    brand_info_to_dict,
    BrandInfo,
    PageContent,
    SUB_PAGE_PATTERNS,
    _fetch_page,
    _extract_title,
    _extract_text,
    _discover_sub_pages,
    _extract_brand_strengths,
)


def _make_page_content(
    url: str = "https://example.com",
    title: str = "Example Corp",
    text: str = "Example Corp는 최고의 서비스를 제공합니다.",
    page_type: str = "main",
) -> PageContent:
    """테스트용 PageContent를 생성합니다."""
    return PageContent(
        url=url,
        title=title,
        text=text,
        page_type=page_type,
    )


def _make_brand_info() -> BrandInfo:
    """테스트용 BrandInfo를 생성합니다."""
    return BrandInfo(
        crawled_at="2026-03-12T10:00:00Z",
        main_page={"title": "Example Corp", "text": "최고의 서비스"},
        sub_pages=[
            {"url": "/about", "title": "회사소개", "text": "회사 소개 내용", "type": "about"},
        ],
        extracted_strengths=["10년 경력", "전문 기술력", "고객 맞춤 서비스"],
        extracted_services=["컨설팅", "개발", "유지보수"],
        brand_tone="professional",
        summary="Example Corp는 전문 IT 서비스 기업입니다.",
    )


class TestSubPagePatterns:
    """SUB_PAGE_PATTERNS 상수 테스트."""

    def test_patterns_exist(self):
        """필수 패턴 존재 확인."""
        assert "about" in SUB_PAGE_PATTERNS
        assert "services" in SUB_PAGE_PATTERNS
        assert "contact" in SUB_PAGE_PATTERNS

    def test_pattern_values(self):
        """패턴 값 확인."""
        assert "about" in SUB_PAGE_PATTERNS["about"]
        assert "회사소개" in SUB_PAGE_PATTERNS["about"]
        assert "service" in SUB_PAGE_PATTERNS["services"]
        assert "서비스" in SUB_PAGE_PATTERNS["services"]


class TestPageContent:
    """PageContent 데이터클래스 테스트."""

    def test_create_page_content(self):
        """PageContent 생성 테스트."""
        page = _make_page_content()

        assert page.url == "https://example.com"
        assert page.title == "Example Corp"
        assert page.page_type == "main"
        assert "최고의 서비스" in page.text


class TestBrandInfo:
    """BrandInfo 데이터클래스 테스트."""

    def test_create_brand_info(self):
        """BrandInfo 생성 테스트."""
        info = _make_brand_info()

        assert info.crawled_at == "2026-03-12T10:00:00Z"
        assert info.main_page["title"] == "Example Corp"
        assert len(info.sub_pages) == 1
        assert len(info.extracted_strengths) == 3
        assert len(info.extracted_services) == 3
        assert info.brand_tone == "professional"


class TestBrandInfoToDict:
    """brand_info_to_dict 변환 테스트."""

    def test_to_dict_conversion(self):
        """BrandInfo → dict 변환 테스트."""
        info = _make_brand_info()
        result = brand_info_to_dict(info)

        assert result["crawled_at"] == "2026-03-12T10:00:00Z"
        assert result["main_page"]["title"] == "Example Corp"
        assert len(result["sub_pages"]) == 1
        assert len(result["extracted_strengths"]) == 3
        assert result["brand_tone"] == "professional"
        assert "summary" in result


class TestExtractTitle:
    """_extract_title 함수 테스트."""

    def test_extract_title_from_title_tag(self):
        """<title> 태그에서 제목 추출."""
        page = MagicMock()
        title_elem = MagicMock()
        title_elem.text = "Example Corp - 최고의 서비스"

        page.css.side_effect = lambda sel: {
            "title": [title_elem],
        }.get(sel, [])

        result = _extract_title(page)
        assert result == "Example Corp - 최고의 서비스"

    def test_extract_title_from_og_title(self):
        """og:title 메타 태그에서 제목 추출."""
        page = MagicMock()
        og_elem = MagicMock()
        og_elem.attrib = {"content": "Example Corp"}

        def css_side_effect(sel):
            if sel == "title":
                return []
            if sel == 'meta[property="og:title"]':
                return [og_elem]
            if sel == "h1":
                return []
            return []

        page.css.side_effect = css_side_effect

        result = _extract_title(page)
        assert result == "Example Corp"

    def test_extract_title_from_h1(self):
        """h1 태그에서 제목 추출."""
        page = MagicMock()
        h1_elem = MagicMock()
        h1_elem.text = "Welcome to Example Corp"

        def css_side_effect(sel):
            if sel == "title":
                return []
            if sel == 'meta[property="og:title"]':
                return []
            if sel == "h1":
                return [h1_elem]
            return []

        page.css.side_effect = css_side_effect

        result = _extract_title(page)
        assert result == "Welcome to Example Corp"


class TestExtractText:
    """_extract_text 함수 테스트."""

    def test_extract_text_from_main(self):
        """<main> 태그에서 텍스트 추출 (충분한 길이)."""
        page = MagicMock()
        main_elem = MagicMock()
        # 100자 이상이어야 유효한 텍스트로 인정됨
        long_text = "  본문  텍스트  입니다.  " * 10
        main_elem.get_all_text.return_value = long_text

        page.css.side_effect = lambda sel: {
            "main": [main_elem],
        }.get(sel, [])

        result = _extract_text(page)
        assert "본문" in result
        assert "텍스트" in result

    def test_extract_text_min_length(self):
        """100자 미만 텍스트는 건너뛰고 다음 셀렉터 시도."""
        page = MagicMock()
        short_elem = MagicMock()
        short_elem.get_all_text.return_value = "짧은 텍스트"

        long_elem = MagicMock()
        long_elem.get_all_text.return_value = "충분히 긴 본문 텍스트입니다. " * 10

        def css_side_effect(sel):
            if sel == "main":
                return [short_elem]
            if sel == "article":
                return [long_elem]
            return []

        page.css.side_effect = css_side_effect

        result = _extract_text(page)
        assert len(result) > 100


class TestDiscoverSubPages:
    """_discover_sub_pages 함수 테스트."""

    def test_discover_about_page(self):
        """About 페이지 탐색 테스트 (page 객체 직접 전달)."""
        base_url = "https://example.com"

        # Mock page 객체 (이미 fetch된 상태)
        mock_page = MagicMock()

        link_about = MagicMock()
        link_about.attrib = {"href": "/about"}
        link_about.text = "회사소개"

        link_external = MagicMock()
        link_external.attrib = {"href": "https://other.com/page"}
        link_external.text = "External"

        mock_page.css.return_value = [link_about, link_external]

        # 이제 page 객체를 직접 전달 (중복 네트워크 요청 없음)
        result = _discover_sub_pages(base_url, mock_page)

        # /about 페이지만 발견되어야 함 (외부 링크 제외)
        assert len(result) >= 1
        urls = [url for url, _ in result]
        assert any("about" in url for url in urls)


class TestExtractBrandStrengths:
    """_extract_brand_strengths 함수 테스트."""

    def test_extract_with_gemini_success(self):
        """Gemini API 성공 시 강점 추출 테스트."""
        main_page = _make_page_content()
        sub_pages = [
            _make_page_content(url="/about", title="회사소개", page_type="about"),
        ]

        mock_response = {
            "strengths": ["10년 경력", "전문 기술력"],
            "services": ["컨설팅", "개발"],
            "tone": "professional",
            "summary": "전문 IT 서비스 기업",
        }

        with patch("src.analyzer.brand_crawler.config") as mock_config:
            mock_config.GOOGLE_AI_API_KEY = "test-key"
            mock_config.GEMINI_ANALYSIS_MODEL = "test-model"

            with patch("src.analyzer.brand_crawler._call_gemini") as mock_gemini:
                mock_gemini.return_value = mock_response

                result = _extract_brand_strengths(main_page, sub_pages, "Example Corp")

                assert result["strengths"] == ["10년 경력", "전문 기술력"]
                assert result["services"] == ["컨설팅", "개발"]
                assert result["tone"] == "professional"

    def test_extract_fallback_on_gemini_failure(self):
        """Gemini API 실패 시 fallback 테스트."""
        main_page = _make_page_content(text="전문 컨설팅 서비스를 제공합니다.")
        sub_pages = []

        with patch("src.analyzer.brand_crawler._call_gemini") as mock_gemini:
            mock_gemini.return_value = None

            result = _extract_brand_strengths(main_page, sub_pages, None)

            # fallback은 기본값 반환
            assert "strengths" in result
            assert "services" in result
            assert result["tone"] == "professional"


class TestCrawlBrandHomepage:
    """crawl_brand_homepage 통합 테스트."""

    def test_crawl_success(self):
        """브랜드 크롤링 성공 테스트."""
        url = "https://example.com"

        # Mock page content와 page 객체
        main_page = _make_page_content()
        about_page = _make_page_content(url="/about", title="회사소개", page_type="about")
        mock_page_obj = MagicMock()

        # Mock Gemini 응답
        mock_gemini_response = {
            "strengths": ["핵심 강점 1", "핵심 강점 2"],
            "services": ["서비스 A", "서비스 B"],
            "tone": "professional",
            "summary": "브랜드 요약",
        }

        with patch("src.analyzer.brand_crawler._fetch_page_with_obj") as mock_fetch_with_obj:
            # 첫 번째 호출: main page와 page 객체 반환
            mock_fetch_with_obj.return_value = (main_page, mock_page_obj)

            with patch("src.analyzer.brand_crawler._fetch_page") as mock_fetch:
                # 서브페이지 크롤링용
                mock_fetch.return_value = about_page

                with patch("src.analyzer.brand_crawler._discover_sub_pages") as mock_discover:
                    mock_discover.return_value = [("https://example.com/about", "about")]

                    with patch("src.analyzer.brand_crawler.config") as mock_config:
                        mock_config.GOOGLE_AI_API_KEY = "test-key"
                        mock_config.GEMINI_ANALYSIS_MODEL = "test-model"

                        with patch("src.analyzer.brand_crawler._call_gemini") as mock_gemini:
                            mock_gemini.return_value = mock_gemini_response

                            result = crawl_brand_homepage(url, "Example Corp", max_sub_pages=1)

                            assert result is not None
                            assert result.main_page["title"] == "Example Corp"
                            assert len(result.extracted_strengths) == 2
                            assert result.brand_tone == "professional"

    def test_crawl_main_page_failure(self):
        """메인 페이지 크롤링 실패 테스트."""
        url = "https://example.com"

        with patch("src.analyzer.brand_crawler._fetch_page_with_obj") as mock_fetch:
            mock_fetch.return_value = (None, None)

            result = crawl_brand_homepage(url)

            assert result is None


class TestFormatBrandInfo:
    """_format_brand_info 프롬프트 포맷팅 테스트."""

    def test_format_brand_info_full(self):
        """전체 브랜드 정보 포맷팅 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand = {
            "summary": "최고의 IT 서비스 기업",
            "brand_tone": "professional",
            "extracted_strengths": ["10년 경력", "전문 기술력"],
            "extracted_services": ["컨설팅", "개발"],
            "main_page": {"title": "Example Corp"},
        }

        result = _format_brand_info(brand)

        assert "최고의 IT 서비스 기업" in result
        assert "전문적이고 신뢰감 있는" in result
        assert "10년 경력" in result
        assert "컨설팅" in result
        assert "Example Corp" in result

    def test_format_brand_info_empty(self):
        """빈 브랜드 정보 포맷팅 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand = {}

        result = _format_brand_info(brand)

        assert result == "브랜드 정보 없음"

    def test_format_brand_info_partial(self):
        """일부 정보만 있는 경우 포맷팅 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand = {
            "brand_tone": "friendly",
            "extracted_strengths": ["정보 없음"],  # 무시됨
            "extracted_services": ["서비스 A"],
        }

        result = _format_brand_info(brand)

        assert "친근하고 따뜻한" in result
        assert "서비스 A" in result
        # "정보 없음"은 무시되어야 함
        assert "핵심 강점" not in result


class TestPromptBuilderBrandInfo:
    """prompt_builder의 brand_info 통합 테스트."""

    def test_build_prompt_with_brand_info(self):
        """brand_info 포함 프롬프트 빌드 테스트."""
        from src.generator.prompt_builder import build_prompt, PatternData

        pattern_data: PatternData = {
            "avg_char_count": 2000,
            "avg_image_count": 5,
            "avg_heading_count": 4,
            "brand_info": {
                "summary": "최고의 서비스",
                "brand_tone": "professional",
                "extracted_strengths": ["강점 1", "강점 2"],
                "extracted_services": ["서비스 A"],
                "main_page": {"title": "Test Corp"},
            },
        }

        result = build_prompt(
            keyword="테스트 키워드",
            pattern_data=pattern_data,
        )

        # 브랜드 정보가 user prompt에 포함되어야 함
        assert "최고의 서비스" in result["user"]
        assert "강점 1" in result["user"]
        assert "서비스 A" in result["user"]

    def test_build_prompt_without_brand_info(self):
        """brand_info 없는 프롬프트 빌드 테스트."""
        from src.generator.prompt_builder import build_prompt

        result = build_prompt(keyword="테스트 키워드")

        # "브랜드 정보 없음"이 포함되어야 함
        assert "브랜드 정보 없음" in result["user"]


@pytest.mark.live
class TestCrawlBrandHomepageLive:
    """실제 API를 사용하는 라이브 테스트.

    실행 방법: pytest tests/test_brand_crawler.py -m live -v
    환경변수: GOOGLE_AI_API_KEY 필요
    """

    def test_crawl_real_homepage(self):
        """실제 웹사이트 크롤링 테스트 (예시)."""
        # 테스트용 공개 웹사이트 URL
        # 실제 테스트 시 적절한 URL로 변경 필요
        url = "https://www.example.com"

        result = crawl_brand_homepage(url, max_sub_pages=2)

        # 성공/실패 여부만 확인 (실제 결과는 사이트에 따라 다름)
        if result:
            assert result.main_page is not None
            assert result.crawled_at is not None
