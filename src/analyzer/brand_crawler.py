"""
브랜드 홈페이지 크롤러 모듈.

Scrapling StealthyFetcher를 사용하여 브랜드 홈페이지를 크롤링하고,
Gemini Flash로 브랜드 강점/서비스를 요약합니다.

CLAUDE.md 라이브러리 역할 분리 원칙:
- Scrapling (StealthyFetcher): 읽기 전용 크롤링만 수행
"""

import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from src import config

logger = logging.getLogger(__name__)


# 서브페이지 탐색 패턴
SUB_PAGE_PATTERNS: dict[str, list[str]] = {
    "about": ["about", "회사소개", "소개", "company", "intro", "기업소개"],
    "services": ["service", "서비스", "product", "제품", "솔루션", "solution"],
    "contact": ["contact", "문의", "오시는길", "찾아오시는", "location"],
    "history": ["history", "연혁", "沿革"],
    "team": ["team", "팀", "구성원", "people", "조직"],
}


@dataclass
class PageContent:
    """단일 페이지 크롤링 결과."""

    url: str
    """페이지 URL"""

    title: str
    """페이지 제목"""

    text: str
    """본문 텍스트 (최대 5000자)"""

    page_type: str
    """페이지 유형: 'main', 'about', 'services' 등"""


@dataclass
class BrandInfo:
    """브랜드 정보 구조."""

    crawled_at: str
    """크롤링 시각 (ISO 8601)"""

    main_page: dict[str, str]
    """메인 페이지 정보: {"title": ..., "text": ...}"""

    sub_pages: list[dict[str, str]]
    """서브페이지 목록: [{"url": ..., "title": ..., "text": ..., "type": ...}]"""

    extracted_strengths: list[str]
    """추출된 브랜드 강점"""

    extracted_services: list[str]
    """추출된 서비스/제품"""

    brand_tone: str
    """브랜드 톤: 'professional', 'friendly', 'luxury' 등"""

    brand_name: str = ""
    """브랜드명 (홈페이지 title에서 자동 추출 또는 수동 입력)"""

    summary: str = ""
    """브랜드 요약 (1~2문장)"""

    programs: list[str] = field(default_factory=list)
    """대표 프로그램/제품명 (예: 다잇단, BB주사 등)"""

    location: dict[str, str] = field(default_factory=dict)
    """위치 정보: {"address": ..., "nearby_station": ..., "landmarks": ...}"""

    stats: list[str] = field(default_factory=list)
    """실적/통계 (예: "114,948명 치료 경험", "20년 전통" 등)"""

    team: list[str] = field(default_factory=list)
    """의료진/전문가 정보"""


def crawl_brand_homepage(
    url: str,
    brand_name: str | None = None,
    max_sub_pages: int = 5,
    timeout: int = 30,
) -> BrandInfo | None:
    """
    브랜드 홈페이지를 크롤링하여 브랜드 정보를 추출합니다.

    Args:
        url: 브랜드 홈페이지 URL
        brand_name: 브랜드명 (선택, 분석 정확도 향상에 사용)
        max_sub_pages: 탐색할 최대 서브페이지 수 (기본값: 5)
        timeout: 페이지 로드 타임아웃 (초)

    Returns:
        BrandInfo 또는 None (실패 시)

    Example:
        >>> info = crawl_brand_homepage("https://example.com", "Example Corp")
        >>> if info:
        ...     print(info.extracted_strengths)
    """
    logger.info(f"브랜드 크롤링 시작: {url}")

    # URL 유효성 검증
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        logger.error(f"잘못된 URL 형식: {url}")
        return None

    # scheme이 http/https가 아닌 경우
    if parsed_url.scheme not in ("http", "https"):
        logger.error(f"지원하지 않는 URL 스킴: {parsed_url.scheme}")
        return None

    try:
        # 1. 메인 페이지 크롤링 (page 객체도 함께 반환)
        main_page, page_obj = _fetch_page_with_obj(url, "main", timeout)
        if not main_page:
            logger.warning(f"메인 페이지 크롤링 실패: {url}")
            return None

        logger.info(f"메인 페이지 크롤링 완료: {main_page.title}")

        # 2. 서브페이지 탐색 및 크롤링 (이미 fetch한 page 객체 재사용)
        sub_pages: list[PageContent] = []
        discovered_urls = _discover_sub_pages(url, page_obj)

        for sub_url, page_type in discovered_urls[:max_sub_pages]:
            logger.info(f"서브페이지 크롤링 중: {sub_url} ({page_type})")
            sub_page = _fetch_page(sub_url, page_type, timeout)
            if sub_page:
                sub_pages.append(sub_page)
            # 봇 탐지 우회를 위한 랜덤 딜레이
            time.sleep(random.uniform(1.5, 3.0))

        logger.info(f"서브페이지 크롤링 완료: {len(sub_pages)}개")

        # 3. Gemini Flash로 브랜드 강점/서비스 추출
        extracted = _extract_brand_strengths(main_page, sub_pages, brand_name)

        # 4. BrandInfo 조립
        # 브랜드명: 수동 입력 > Gemini 추출 > 홈페이지 title 자동 추출
        resolved_brand_name = brand_name or extracted.get("brand_name", "") or main_page.title.split("|")[0].split("-")[0].strip()

        brand_info = BrandInfo(
            crawled_at=datetime.now(timezone.utc).isoformat(),
            brand_name=resolved_brand_name,
            main_page={
                "title": main_page.title,
                "text": main_page.text[:2000],
            },
            sub_pages=[
                {
                    "url": sp.url,
                    "title": sp.title,
                    "text": sp.text[:1500],
                    "type": sp.page_type,
                }
                for sp in sub_pages
            ],
            extracted_strengths=extracted.get("strengths", []),
            extracted_services=extracted.get("services", []),
            brand_tone=extracted.get("tone", "professional"),
            summary=extracted.get("summary", ""),
            programs=extracted.get("programs", []),
            location=extracted.get("location", {}),
            stats=extracted.get("stats", []),
            team=extracted.get("team", []),
        )

        logger.info(
            f"브랜드 크롤링 완료: 강점={len(brand_info.extracted_strengths)}, "
            f"서비스={len(brand_info.extracted_services)}"
        )

        return brand_info

    except Exception as e:
        logger.error(f"브랜드 크롤링 오류: {url} - {e}")
        return None


def _fetch_page_with_obj(url: str, page_type: str, timeout: int) -> tuple[PageContent | None, Any]:
    """
    단일 페이지를 크롤링하고 page 객체도 함께 반환합니다.

    Args:
        url: 페이지 URL
        page_type: 페이지 유형 ('main', 'about', 'services' 등)
        timeout: 타임아웃 (초)

    Returns:
        (PageContent, page_obj) 또는 (None, None) (실패 시)
    """
    try:
        from scrapling import StealthyFetcher
    except ImportError:
        logger.error("scrapling 패키지가 설치되지 않았습니다.")
        return None, None

    try:
        fetcher = StealthyFetcher()
        page = fetcher.fetch(url, timeout=timeout * 1000)

        if page is None or page.status != 200:
            logger.warning(
                f"페이지 로드 실패: {url}, status={getattr(page, 'status', None)}"
            )
            return None, None

        # 제목 추출
        title = _extract_title(page)

        # 본문 텍스트 추출
        text = _extract_text(page)

        content = PageContent(
            url=url,
            title=title,
            text=text[:5000],  # 최대 5000자
            page_type=page_type,
        )

        return content, page

    except Exception as e:
        logger.error(f"페이지 크롤링 오류: {url} - {e}")
        return None, None


def _fetch_page(url: str, page_type: str, timeout: int) -> PageContent | None:
    """
    단일 페이지를 크롤링합니다.

    Args:
        url: 페이지 URL
        page_type: 페이지 유형 ('main', 'about', 'services' 등)
        timeout: 타임아웃 (초)

    Returns:
        PageContent 또는 None (실패 시)
    """
    content, _ = _fetch_page_with_obj(url, page_type, timeout)
    return content


def _extract_title(page) -> str:
    """페이지 제목을 추출합니다."""
    # 1. <title> 태그
    try:
        title_tags = page.css("title")
        if title_tags:
            text = getattr(title_tags[0], 'text', '') or ''
            if text.strip():
                return text.strip()
    except Exception:
        pass

    # 2. og:title 메타 태그
    try:
        og_title = page.css('meta[property="og:title"]')
        if og_title:
            return og_title[0].attrib.get("content", "")
    except Exception:
        pass

    # 3. h1 태그
    try:
        h1_tags = page.css("h1")
        if h1_tags:
            text = getattr(h1_tags[0], 'text', '') or ''
            if text.strip():
                return text.strip()
    except Exception:
        pass

    return ""


def _extract_text(page) -> str:
    """페이지 본문 텍스트를 추출합니다."""
    # 메인 콘텐츠 영역 우선 탐색
    content_selectors = [
        "main",
        "article",
        "#content",
        ".content",
        "#main",
        ".main",
        ".container",
        "body",
    ]

    for selector in content_selectors:
        try:
            elements = page.css(selector)
            if elements:
                text = ""
                if hasattr(elements[0], "get_all_text"):
                    text = elements[0].get_all_text() or ""
                elif hasattr(elements[0], "text_content"):
                    text = elements[0].text_content() or ""
                elif hasattr(elements[0], "text"):
                    text = elements[0].text or ""

                # Zero-width 문자 및 연속 공백 정리
                text = text.replace("\u200b", "")
                text = re.sub(r"\s+", " ", text)
                text = text.strip()

                if len(text) > 100:  # 최소 100자 이상일 때만 유효
                    return text
        except Exception:
            continue

    return ""


def _discover_sub_pages(
    base_url: str,
    page: Any,
) -> list[tuple[str, str]]:
    """
    이미 fetch한 page 객체에서 서브페이지 URL을 탐색합니다.

    Args:
        base_url: 기준 URL (상대경로 변환용)
        page: scrapling page 객체 (이미 fetch된 상태)

    Returns:
        [(url, page_type), ...] 형태의 리스트
    """
    discovered: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    if page is None:
        return []

    try:
        # 모든 링크 추출 (이미 fetch한 page 객체 재사용)
        links = page.css("a[href]")

        for link in links:
            href = link.attrib.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            # 절대 URL로 변환
            full_url = urljoin(base_url, href)

            # 같은 도메인 내 링크만
            if urlparse(full_url).netloc != urlparse(base_url).netloc:
                continue

            # 중복 제거
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # 링크 텍스트 및 URL 패턴 분석
            link_text = (link.text or "").lower()
            href_lower = href.lower()

            for page_type, patterns in SUB_PAGE_PATTERNS.items():
                if any(p in link_text or p in href_lower for p in patterns):
                    discovered.append((full_url, page_type))
                    break

    except Exception as e:
        logger.warning(f"서브페이지 탐색 오류: {e}")

    return discovered


def _extract_brand_strengths(
    main_page: PageContent,
    sub_pages: list[PageContent],
    brand_name: str | None,
) -> dict[str, Any]:
    """
    Gemini Flash로 브랜드 강점/서비스를 추출합니다.

    Args:
        main_page: 메인 페이지 콘텐츠
        sub_pages: 서브페이지 콘텐츠 목록
        brand_name: 브랜드명 (선택)

    Returns:
        {
            "strengths": [...],
            "services": [...],
            "tone": "...",
            "summary": "..."
        }
    """
    if not config.GOOGLE_AI_API_KEY:
        logger.warning("GOOGLE_AI_API_KEY가 설정되지 않았습니다. 기본값 반환.")
        return _fallback_extraction(main_page, sub_pages)

    # 프롬프트 구성
    all_text = f"## 메인 페이지: {main_page.title}\n{main_page.text[:2000]}\n\n"
    for sp in sub_pages[:3]:  # 최대 3개 서브페이지
        all_text += f"## {sp.page_type} 페이지: {sp.title}\n{sp.text[:1000]}\n\n"

    brand_hint = f"브랜드명: {brand_name}\n" if brand_name else ""

    prompt = f"""다음은 기업/브랜드 홈페이지에서 크롤링한 텍스트입니다.
{brand_hint}
이 브랜드의 핵심 강점, 서비스/제품, 브랜드 톤, 위치 정보, 실적 등을 분석해주세요.

{all_text}

## 분석 요청
위 내용을 분석하여 아래 JSON 형식으로 응답해주세요. 정보가 없는 필드는 빈 배열/객체로 반환:

{{
    "strengths": ["핵심 강점/차별점 3~5개 (짧은 문장)"],
    "services": ["주요 서비스/제품 3~5개"],
    "programs": ["대표 프로그램/제품 이름 (예: 다잇단, BB주사, 맞춤한약 등)"],
    "stats": ["실적/통계 숫자 (예: '114,948명 치료', '20년 전통', '만족도 98%' 등)"],
    "location": {{
        "address": "주소 (있으면)",
        "nearby_station": "인근 지하철역 (있으면)",
        "landmarks": "주변 랜드마크 (있으면, 쉼표 구분)"
    }},
    "team": ["대표 의료진/전문가 이름 및 약력 (있으면)"],
    "tone": "브랜드 톤 (professional/friendly/luxury/innovative/traditional 중 택1)",
    "summary": "브랜드 한줄 요약 (20~40자)"
}}"""

    try:
        result = _call_gemini(prompt)
        if result:
            return {
                "strengths": result.get("strengths", []),
                "services": result.get("services", []),
                "programs": result.get("programs", []),
                "stats": result.get("stats", []),
                "location": result.get("location", {}),
                "team": result.get("team", []),
                "tone": result.get("tone", "professional"),
                "summary": result.get("summary", ""),
            }
    except Exception as e:
        logger.error(f"Gemini 분석 오류: {e}")

    return _fallback_extraction(main_page, sub_pages)


def _fallback_extraction(
    main_page: PageContent,
    sub_pages: list[PageContent],
) -> dict[str, Any]:
    """
    Gemini 호출 실패 시 기본 텍스트 분석으로 fallback.

    단순 키워드 기반 추출.
    """
    all_text = main_page.text
    for sp in sub_pages:
        all_text += " " + sp.text

    # 간단한 키워드 추출
    strengths: list[str] = []
    services: list[str] = []

    # 강점 관련 패턴
    strength_patterns = [
        r"최고의?\s*(.{5,30})",
        r"전문\s*(.{5,20})",
        r"(\d+년\s*경력)",
        r"(\d+건\s*이상)",
        r"No\.?\s*1\s*(.{3,20})",
        r"업계\s*(.{3,15})",
    ]

    for pattern in strength_patterns:
        matches = re.findall(pattern, all_text)
        for match in matches[:2]:
            if match and len(match.strip()) >= 3:
                strengths.append(match.strip())

    # 서비스/제품 관련 패턴
    service_patterns = [
        r"서비스\s*[:：]?\s*(.{3,20})",
        r"제품\s*[:：]?\s*(.{3,20})",
        r"솔루션\s*[:：]?\s*(.{3,20})",
        r"(.{2,15})\s*서비스",
        r"(.{2,15})\s*솔루션",
        r"(.{2,15})\s*컨설팅",
        r"(.{2,15})\s*프로그램",
    ]

    for pattern in service_patterns:
        matches = re.findall(pattern, all_text)
        for match in matches[:2]:
            if match and len(match.strip()) >= 2:
                services.append(match.strip())

    # 중복 제거
    strengths = list(dict.fromkeys(strengths))
    services = list(dict.fromkeys(services))

    return {
        "strengths": strengths[:5] if strengths else ["정보 없음"],
        "services": services[:5] if services else ["정보 없음"],
        "programs": [],
        "stats": [],
        "location": {},
        "team": [],
        "tone": "professional",
        "summary": main_page.title[:40] if main_page.title else "",
    }


def _call_gemini(prompt: str, max_retries: int = 3) -> dict[str, Any] | None:
    """Gemini API를 호출하여 JSON 응답을 파싱합니다."""
    backoff_seconds = [10, 30, 60]

    for attempt in range(max_retries):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=config.GOOGLE_AI_API_KEY)
            response = client.models.generate_content(
                model=config.GEMINI_ANALYSIS_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    response_mime_type="application/json",
                ),
            )

            if not response or not response.text:
                logger.warning("Gemini 응답이 비어있습니다.")
                return None

            return json.loads(response.text)

        except json.JSONDecodeError as e:
            logger.error(f"Gemini JSON 파싱 오류: {e}")
            return None
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = backoff_seconds[attempt]
                logger.warning(
                    f"Gemini 429 rate limit, {wait}초 후 재시도 ({attempt + 1}/{max_retries})..."
                )
                time.sleep(wait)
                continue
            logger.error(f"Gemini API 호출 오류: {e}")
            return None

    return None


def brand_info_to_dict(info: BrandInfo) -> dict[str, Any]:
    """BrandInfo를 딕셔너리로 변환합니다."""
    return {
        "crawled_at": info.crawled_at,
        "brand_name": info.brand_name,
        "main_page": info.main_page,
        "sub_pages": info.sub_pages,
        "extracted_strengths": info.extracted_strengths,
        "extracted_services": info.extracted_services,
        "brand_tone": info.brand_tone,
        "summary": info.summary,
        "programs": info.programs,
        "location": info.location,
        "stats": info.stats,
        "team": info.team,
    }
