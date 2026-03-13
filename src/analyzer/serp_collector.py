"""
SERP(검색 결과 페이지) 수집 모듈.

네이버 블로그 검색 API를 통해 키워드 상위 블로그 URL을 수집합니다.
API 실패 시 Scrapling StealthyFetcher로 직접 크롤링합니다.
"""

import logging
import time
from typing import Optional

from src.utils.naver_api import search_blog

logger = logging.getLogger(__name__)

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def collect_top_urls(
    keyword: str,
    count: int = 5,
    use_fallback: bool = True,
) -> list[str]:
    """
    키워드로 네이버 블로그 검색하여 상위 URL을 수집합니다.

    Args:
        keyword: 검색할 키워드
        count: 수집할 URL 개수 (기본값: 5)
        use_fallback: API 실패 시 크롤링 폴백 사용 여부

    Returns:
        블로그 URL 리스트. 실패 시 빈 리스트.

    Example:
        >>> urls = collect_top_urls("강남 맛집", count=5)
        >>> print(urls)
        ['https://blog.naver.com/...', ...]
    """
    logger.info(f"SERP 수집 시작: keyword='{keyword}', count={count}")

    # 1. 네이버 검색 API 시도
    urls = _collect_via_api(keyword, count)

    if urls:
        logger.info(f"API로 {len(urls)}개 URL 수집 완료")
        return urls

    # 2. 폴백: Scrapling 직접 크롤링
    if use_fallback:
        logger.warning("API 실패, Scrapling 폴백 시도")
        urls = _collect_via_scraping(keyword, count)

        if urls:
            logger.info(f"크롤링으로 {len(urls)}개 URL 수집 완료")
            return urls

    logger.error(f"SERP 수집 실패: keyword='{keyword}'")
    return []


def _collect_via_api(keyword: str, count: int) -> list[str]:
    """네이버 검색 API를 통한 URL 수집."""
    try:
        results = search_blog(keyword, display=count)

        if not results:
            logger.warning(f"API 결과 없음: keyword='{keyword}'")
            return []

        urls = []
        for item in results:
            link = item.get("link", "")
            # 네이버 블로그 URL만 필터링
            if "blog.naver.com" in link:
                urls.append(link)

        return urls[:count]

    except Exception as e:
        logger.error(f"네이버 API 호출 실패: {e}")
        return []


def _collect_via_scraping(keyword: str, count: int) -> list[str]:
    """
    Scrapling StealthyFetcher를 통한 직접 크롤링.

    네이버 검색 결과 페이지를 직접 크롤링하여 블로그 URL을 추출합니다.
    """
    try:
        from scrapling import StealthyFetcher
    except ImportError:
        logger.error("scrapling 패키지가 설치되지 않았습니다. pip install scrapling")
        return []

    search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"크롤링 시도 {attempt}/{MAX_RETRIES}: {search_url}")

            fetcher = StealthyFetcher(
                headless=True,
                network_idle=True,
                auto_save=True,
            )

            page = fetcher.fetch(search_url)

            if page is None or page.status != 200:
                logger.warning(f"페이지 로드 실패: status={getattr(page, 'status', None)}")
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue

            # 블로그 검색 결과에서 URL 추출
            urls = _extract_blog_urls_from_serp(page, count)

            if urls:
                return urls

            logger.warning(f"URL 추출 실패, 재시도 대기 중...")
            time.sleep(RETRY_DELAY_SECONDS * attempt)

        except Exception as e:
            logger.error(f"크롤링 오류 (시도 {attempt}): {e}")
            time.sleep(RETRY_DELAY_SECONDS * attempt)

    return []


def _extract_blog_urls_from_serp(page, count: int) -> list[str]:
    """
    네이버 검색 결과 페이지에서 블로그 URL을 추출합니다.

    Args:
        page: Scrapling 페이지 객체
        count: 추출할 URL 개수

    Returns:
        블로그 URL 리스트
    """
    urls = []

    # 네이버 블로그 검색 결과 셀렉터들
    selectors = [
        "a.api_txt_lines.total_tit",  # 새 UI
        "a.sh_blog_title",  # 구 UI
        ".total_wrap a.total_tit",  # 대체 셀렉터
        "a[href*='blog.naver.com']",  # 범용 셀렉터
    ]

    for selector in selectors:
        try:
            elements = page.css(selector)
            if elements:
                for elem in elements:
                    href = elem.attrib.get("href", "")
                    if href and "blog.naver.com" in href:
                        # 중복 제거
                        if href not in urls:
                            urls.append(href)
                        if len(urls) >= count:
                            return urls[:count]
        except Exception as e:
            logger.debug(f"셀렉터 '{selector}' 실패: {e}")
            continue

    return urls[:count]


def validate_url(url: str) -> bool:
    """
    URL이 유효한 네이버 블로그 URL인지 검증합니다.

    Args:
        url: 검증할 URL

    Returns:
        유효하면 True
    """
    if not url:
        return False

    valid_patterns = [
        "blog.naver.com/",
        "m.blog.naver.com/",
    ]

    return any(pattern in url for pattern in valid_patterns)
