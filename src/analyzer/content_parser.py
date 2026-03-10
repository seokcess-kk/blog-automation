"""
블로그 콘텐츠 파싱 모듈.

Scrapling StealthyFetcher를 사용하여 네이버 블로그 본문을 분석합니다.
SE 에디터와 구 에디터 DOM 구조를 모두 지원합니다.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedContent:
    """파싱된 블로그 콘텐츠 구조."""

    url: str
    """블로그 포스트 URL"""

    title: str
    """포스트 제목"""

    char_count: int
    """본문 글자 수 (공백 제외)"""

    image_count: int
    """이미지 개수"""

    heading_count: int
    """소제목(h2, h3, 강조 텍스트) 개수"""

    headings: list[str]
    """소제목 텍스트 목록"""

    keyword_in_title: bool
    """제목에 키워드 포함 여부"""

    keyword_positions: list[int]
    """본문 내 키워드 위치 (문자 인덱스)"""

    image_positions: list[float]
    """이미지 위치 비율 (0.0~1.0, 본문 대비 상대 위치)"""

    has_list: bool
    """목록(ul/ol) 포함 여부"""

    has_table: bool
    """테이블 포함 여부"""

    related_keywords: list[str]
    """연관 키워드 (본문에서 추출)"""

    raw_text: str = ""
    """원본 텍스트 (디버깅용)"""


def parse_blog_content(
    url: str,
    keyword: str,
    timeout: int = 30,
) -> Optional[ParsedContent]:
    """
    블로그 URL에서 콘텐츠를 파싱합니다.

    Args:
        url: 블로그 포스트 URL
        keyword: 분석 대상 키워드
        timeout: 페이지 로드 타임아웃 (초)

    Returns:
        파싱된 콘텐츠 또는 None (실패 시)

    Example:
        >>> content = parse_blog_content(
        ...     "https://blog.naver.com/example/123",
        ...     keyword="맛집"
        ... )
        >>> print(content.char_count, content.image_count)
    """
    logger.info(f"콘텐츠 파싱 시작: {url}")

    try:
        from scrapling import StealthyFetcher
    except ImportError:
        logger.error("scrapling 패키지가 설치되지 않았습니다.")
        return None

    try:
        fetcher = StealthyFetcher(
            headless=True,
            network_idle=True,
            auto_save=True,
        )

        page = fetcher.fetch(url, timeout=timeout * 1000)

        if page is None or page.status != 200:
            logger.warning(f"페이지 로드 실패: {url}, status={getattr(page, 'status', 'None')}")
            return None

        # 본문 컨테이너 추출 (SE 에디터 / 구 에디터)
        main_content = _extract_main_content(page)

        if not main_content:
            logger.warning(f"본문 추출 실패: {url}")
            return None

        # 제목 추출
        title = _extract_title(page)

        # 텍스트 추출
        raw_text = _extract_text(main_content)
        char_count = len(raw_text.replace(" ", "").replace("\n", ""))

        # 이미지 분석
        images = _extract_images(main_content)
        image_count = len(images)
        image_positions = _calculate_image_positions(main_content, images)

        # 소제목 분석
        headings = _extract_headings(main_content)
        heading_count = len(headings)

        # 키워드 분석
        keyword_lower = keyword.lower()
        keyword_in_title = keyword_lower in title.lower()
        keyword_positions = _find_keyword_positions(raw_text, keyword)

        # 구조 분석
        has_list = _has_list_elements(main_content)
        has_table = _has_table_elements(main_content)

        # 연관 키워드 추출
        related_keywords = _extract_related_keywords(raw_text, keyword)

        result = ParsedContent(
            url=url,
            title=title,
            char_count=char_count,
            image_count=image_count,
            heading_count=heading_count,
            headings=headings,
            keyword_in_title=keyword_in_title,
            keyword_positions=keyword_positions,
            image_positions=image_positions,
            has_list=has_list,
            has_table=has_table,
            related_keywords=related_keywords,
            raw_text=raw_text[:1000],  # 처음 1000자만 저장
        )

        logger.info(
            f"파싱 완료: {url} - "
            f"글자수={char_count}, 이미지={image_count}, 소제목={heading_count}"
        )

        return result

    except Exception as e:
        logger.error(f"콘텐츠 파싱 오류: {url} - {e}")
        return None


def _extract_main_content(page) -> Optional[Any]:
    """
    메인 콘텐츠 컨테이너를 추출합니다.

    SE 에디터와 구 에디터 DOM 구조를 모두 지원합니다.
    """
    # SE 에디터 (새 에디터)
    se_selectors = [
        ".se-main-container",
        ".se_component_wrap",
        "#post-view",
    ]

    for selector in se_selectors:
        try:
            elements = page.css(selector)
            if elements:
                return elements[0]
        except Exception:
            continue

    # 구 에디터
    old_selectors = [
        "#postViewArea",
        ".post-view",
        "#post_1",
        ".se_doc_viewer",
    ]

    for selector in old_selectors:
        try:
            elements = page.css(selector)
            if elements:
                return elements[0]
        except Exception:
            continue

    # iframe 내부 확인 (구 에디터)
    try:
        iframes = page.css("iframe#mainFrame")
        if iframes:
            # iframe 내부 콘텐츠 접근 시도
            logger.debug("iframe 내부 콘텐츠 접근 시도")
            # Scrapling에서 iframe 처리가 제한적일 수 있음
    except Exception:
        pass

    return None


def _extract_title(page) -> str:
    """포스트 제목을 추출합니다."""
    title_selectors = [
        ".se-title-text",
        ".pcol1 > span",
        "#title_1",
        "h3.tit_h3",
        ".tit_view",
    ]

    for selector in title_selectors:
        try:
            elements = page.css(selector)
            if elements:
                text = elements[0].text.strip()
                if text:
                    return text
        except Exception:
            continue

    # og:title 메타 태그 폴백
    try:
        og_title = page.css('meta[property="og:title"]')
        if og_title:
            return og_title[0].attrib.get("content", "")
    except Exception:
        pass

    return ""


def _extract_text(container) -> str:
    """컨테이너에서 텍스트를 추출합니다."""
    try:
        # 모든 텍스트 노드 추출
        text = container.text_content() or ""
        # 연속 공백 정리
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        logger.debug(f"텍스트 추출 오류: {e}")
        return ""


def _extract_images(container) -> list:
    """컨테이너 내 이미지 요소를 추출합니다."""
    images = []

    img_selectors = [
        "img.se-image-resource",  # SE 에디터
        "img[src*='blogfiles']",  # 네이버 블로그 이미지
        "img[src*='postfiles']",
        ".se_mediaImage img",
        "img",  # 범용
    ]

    for selector in img_selectors:
        try:
            elements = container.css(selector)
            for elem in elements:
                src = elem.attrib.get("src", "") or elem.attrib.get("data-src", "")
                # 아이콘/이모티콘 제외
                if src and not _is_icon_image(src):
                    if elem not in images:
                        images.append(elem)
        except Exception:
            continue

    return images


def _is_icon_image(src: str) -> bool:
    """아이콘/이모티콘 이미지인지 확인합니다."""
    icon_patterns = [
        "icon",
        "emoji",
        "emoticon",
        "btn_",
        "bullet",
        "static.naver",
    ]
    src_lower = src.lower()
    return any(pattern in src_lower for pattern in icon_patterns)


def _calculate_image_positions(container, images: list) -> list[float]:
    """
    이미지의 상대적 위치를 계산합니다.

    Returns:
        각 이미지의 위치 비율 (0.0 = 상단, 1.0 = 하단)
    """
    if not images:
        return []

    positions = []

    try:
        # 전체 콘텐츠 내 이미지 순서 기반 위치 계산
        total = len(images)
        for i, _ in enumerate(images):
            position = i / max(total, 1)
            positions.append(round(position, 2))
    except Exception as e:
        logger.debug(f"이미지 위치 계산 오류: {e}")

    return positions


def _extract_headings(container) -> list[str]:
    """소제목을 추출합니다."""
    headings = []

    heading_selectors = [
        ".se-text-paragraph-align-center",  # SE 에디터 중앙 정렬 텍스트
        "h2",
        "h3",
        "strong",
        "b",
        ".se-section-title",
    ]

    for selector in heading_selectors:
        try:
            elements = container.css(selector)
            for elem in elements:
                text = elem.text.strip() if hasattr(elem, 'text') else ""
                # 짧은 텍스트만 소제목으로 간주 (5~50자)
                if text and 5 <= len(text) <= 50:
                    if text not in headings:
                        headings.append(text)
        except Exception:
            continue

    return headings[:10]  # 최대 10개


def _find_keyword_positions(text: str, keyword: str) -> list[int]:
    """본문 내 키워드 위치를 찾습니다."""
    positions = []
    keyword_lower = keyword.lower()
    text_lower = text.lower()

    start = 0
    while True:
        pos = text_lower.find(keyword_lower, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    return positions


def _has_list_elements(container) -> bool:
    """목록 요소 포함 여부를 확인합니다."""
    try:
        ul_elements = container.css("ul")
        ol_elements = container.css("ol")
        return bool(ul_elements or ol_elements)
    except Exception:
        return False


def _has_table_elements(container) -> bool:
    """테이블 요소 포함 여부를 확인합니다."""
    try:
        tables = container.css("table")
        return bool(tables)
    except Exception:
        return False


def _extract_related_keywords(text: str, main_keyword: str) -> list[str]:
    """
    본문에서 연관 키워드를 추출합니다.

    명사 추출 기반의 간단한 키워드 추출.
    """
    related = []

    # 한글 명사 패턴 (2~5글자)
    pattern = r'[가-힣]{2,5}'
    candidates = re.findall(pattern, text)

    # 빈도 계산
    freq: dict[str, int] = {}
    for word in candidates:
        if word != main_keyword and len(word) >= 2:
            freq[word] = freq.get(word, 0) + 1

    # 빈도순 정렬, 상위 10개
    sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)

    # 불용어 필터링
    stopwords = {
        "그리고", "하지만", "그래서", "때문에", "이것은", "그것은",
        "합니다", "입니다", "있습니다", "됩니다", "습니다",
    }

    for word, count in sorted_keywords:
        if word not in stopwords and count >= 2:
            related.append(word)
            if len(related) >= 10:
                break

    return related


def content_to_dict(content: ParsedContent) -> dict:
    """ParsedContent를 딕셔너리로 변환합니다."""
    return {
        "url": content.url,
        "title": content.title,
        "char_count": content.char_count,
        "image_count": content.image_count,
        "heading_count": content.heading_count,
        "headings": content.headings,
        "keyword_in_title": content.keyword_in_title,
        "keyword_positions": content.keyword_positions,
        "image_positions": content.image_positions,
        "has_list": content.has_list,
        "has_table": content.has_table,
        "related_keywords": content.related_keywords,
    }
