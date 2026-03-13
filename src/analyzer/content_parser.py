"""
블로그 콘텐츠 파싱 모듈.

Scrapling StealthyFetcher를 사용하여 네이버 블로그 본문을 분석합니다.
SE 에디터와 구 에디터 DOM 구조를 모두 지원합니다.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


def _convert_to_postview_url(url: str) -> str:
    """
    네이버 블로그 URL을 PostView.naver 형식으로 변환합니다.

    iframe 내부 콘텐츠에 직접 접근하기 위해 필요합니다.

    Examples:
        https://blog.naver.com/username/123456789
        -> https://blog.naver.com/PostView.naver?blogId=username&logNo=123456789
    """
    parsed = urlparse(url)

    # 이미 PostView.naver 형식인 경우
    if "PostView.naver" in url or "PostView.nhn" in url:
        return url

    # blog.naver.com/username/postId 형식 처리
    path_parts = parsed.path.strip("/").split("/")

    if len(path_parts) >= 2:
        blog_id = path_parts[0]
        log_no = path_parts[1]

        # 숫자인지 확인 (postId)
        if log_no.isdigit():
            return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

    # 변환 불가능한 경우 원본 반환
    return url


@dataclass
class ContentSection:
    """본문의 한 섹션 (소제목 ~ 다음 소제목 사이)."""

    heading: str
    """섹션 소제목 ("" = 도입부)"""

    heading_tag: str
    """h2, h3, strong, "" 등"""

    text: str
    """섹션 본문 텍스트"""

    char_count: int
    """섹션 글자 수"""

    image_count: int
    """이 섹션의 이미지 개수"""

    image_contexts: list[str]
    """각 이미지 전후 텍스트 (~100자)"""

    order_index: int
    """섹션 순서 (0-based)"""


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

    sections: list[ContentSection] = field(default_factory=list)
    """섹션별 구조 데이터 (심층 분석용)"""

    full_text: str = ""
    """전체 본문 텍스트 (제한 없음, 심층 분석용)"""


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
    # URL을 PostView.naver 형식으로 변환 (iframe 우회)
    converted_url = _convert_to_postview_url(url)
    if converted_url != url:
        logger.debug(f"URL 변환: {url} -> {converted_url}")

    logger.info(f"콘텐츠 파싱 시작: {converted_url}")

    try:
        from scrapling import StealthyFetcher
    except ImportError:
        logger.error("scrapling 패키지가 설치되지 않았습니다.")
        return None

    try:
        fetcher = StealthyFetcher()

        page = fetcher.fetch(converted_url, timeout=timeout * 1000)

        if page is None or page.status != 200:
            logger.warning(f"페이지 로드 실패: {url}, status={getattr(page, 'status', None)}")
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

        # 섹션 추출 (심층 분석용)
        sections = _extract_sections(main_content)

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
            raw_text=raw_text[:1000],
            sections=sections,
            full_text=raw_text,
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
                text = getattr(elements[0], 'text', '') or ''
                text = text.strip()
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
        # scrapling의 get_all_text() 메서드 사용
        if hasattr(container, 'get_all_text'):
            text = container.get_all_text() or ""
        elif hasattr(container, 'text_content'):
            text = container.text_content() or ""
        else:
            text = container.text or ""

        # Zero-width 문자 및 연속 공백 정리
        text = text.replace('\u200b', '')  # Zero-width space 제거
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        logger.debug(f"텍스트 추출 오류: {e}")
        return ""


def _extract_images(container) -> list:
    """컨테이너 내 콘텐츠 이미지 요소를 추출합니다 (장식용 제외)."""
    images = []
    seen_srcs: set[str] = set()

    # 우선 셀렉터: 네이버 블로그 콘텐츠 이미지
    priority_selectors = [
        "img.se-image-resource",  # SE 에디터
        "img[src*='blogfiles']",  # 네이버 블로그 이미지
        "img[src*='postfiles']",
    ]

    for selector in priority_selectors:
        try:
            elements = container.css(selector)
            for elem in elements:
                src = elem.attrib.get("src", "") or elem.attrib.get("data-src", "")
                if src and src not in seen_srcs and not _is_icon_image(src) and not _is_small_image(elem):
                    seen_srcs.add(src)
                    images.append(elem)
        except Exception:
            continue

    # fallback: 우선 셀렉터로 이미지를 못 찾은 경우에만 generic img 사용
    if not images:
        try:
            elements = container.css("img")
            for elem in elements:
                src = elem.attrib.get("src", "") or elem.attrib.get("data-src", "")
                if src and src not in seen_srcs and not _is_icon_image(src) and not _is_small_image(elem):
                    seen_srcs.add(src)
                    images.append(elem)
        except Exception:
            pass

    return images


def _is_icon_image(src: str) -> bool:
    """아이콘/이모티콘/장식용 이미지인지 확인합니다."""
    icon_patterns = [
        "icon", "emoji", "emoticon", "btn_", "bullet", "static.naver",
        "/separator", "/divider", "/spacer", "/blank", "transparent",
        "_logo", "/logo", "/badge", "sticker", "deco", "bg_", "/background",
        "_arrow", "/arrow", "_check.", "/dot.", "_dot_", "widget", "/banner",
        "profile_", "thumb_", "s.pstatic.net",
    ]
    src_lower = src.lower()
    return any(pattern in src_lower for pattern in icon_patterns)


def _is_small_image(elem) -> bool:
    """크기가 작은 장식용 이미지인지 확인합니다 (width와 height 모두 100px 미만)."""
    threshold = 100

    def _parse_dimension(attr_name: str) -> int | None:
        """속성 또는 inline style에서 크기를 파싱합니다."""
        val = elem.attrib.get(attr_name, "")
        if val:
            try:
                return int(val.replace("px", ""))
            except (ValueError, TypeError):
                pass
        style = elem.attrib.get("style", "")
        if style:
            match = re.search(rf'{attr_name}\s*:\s*(\d+)\s*px', style)
            if match:
                return int(match.group(1))
        return None

    w = _parse_dimension("width")
    h = _parse_dimension("height")

    # 둘 다 파싱된 경우: 모두 작아야 장식용
    if w is not None and h is not None:
        return w < threshold and h < threshold
    # 하나만 파싱된 경우: 다른 축 크기를 알 수 없으므로 필터하지 않음

    return False


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


def _extract_sections(container) -> list['ContentSection']:
    """
    본문을 섹션 단위로 분리합니다.

    SE 에디터: .se-component 순회 (se-text, se-image 등)
    구 에디터: p, h2, h3, img 태그 순서대로 워킹
    """
    sections: list[ContentSection] = []
    current_heading = ""
    current_heading_tag = ""
    current_texts: list[str] = []
    current_image_count = 0
    current_image_contexts: list[str] = []
    section_index = 0

    def _flush_section():
        nonlocal section_index, current_heading, current_heading_tag
        nonlocal current_texts, current_image_count, current_image_contexts
        text = " ".join(current_texts).strip()
        if text or current_image_count > 0:
            sections.append(ContentSection(
                heading=current_heading,
                heading_tag=current_heading_tag,
                text=text,
                char_count=len(text.replace(" ", "").replace("\n", "")),
                image_count=current_image_count,
                image_contexts=current_image_contexts,
                order_index=section_index,
            ))
            section_index += 1
        current_heading = ""
        current_heading_tag = ""
        current_texts = []
        current_image_count = 0
        current_image_contexts = []

    try:
        # SE 에디터 (.se-component 기반)
        components = container.css(".se-component")
        if components:
            for comp in components:
                # 제목 영역 스킵
                classes = comp.attrib.get("class", "")
                if "se-documentTitle" in classes:
                    continue

                # 텍스트 컴포넌트
                if "se-text" in classes:
                    # h2/h3 확인
                    found_heading = False
                    for tag in ("h2", "h3"):
                        heading_elems = comp.css(tag)
                        if heading_elems:
                            heading_text = heading_elems[0].text.strip() if hasattr(heading_elems[0], 'text') else ""
                            if heading_text and 3 <= len(heading_text) <= 80:
                                _flush_section()
                                current_heading = heading_text
                                current_heading_tag = tag
                                found_heading = True
                                break

                    # strong/b 소제목 (h2/h3가 없을 때만)
                    if not found_heading:
                        strong_elems = comp.css("strong, b")
                        for s in strong_elems:
                            s_text = s.text.strip() if hasattr(s, 'text') else ""
                            if s_text and 5 <= len(s_text) <= 50:
                                _flush_section()
                                current_heading = s_text
                                current_heading_tag = "strong"
                                break

                    # 본문 텍스트 추출
                    text = ""
                    if hasattr(comp, 'get_all_text'):
                        text = comp.get_all_text() or ""
                    elif hasattr(comp, 'text'):
                        text = comp.text or ""
                    text = text.strip()
                    if text:
                        current_texts.append(text)

                # 이미지 컴포넌트
                elif "se-image" in classes or "se-imageStrip" in classes:
                    imgs = comp.css("img")
                    valid_imgs = [
                        img for img in imgs
                        if not _is_icon_image(img.attrib.get("src", ""))
                        and not _is_small_image(img)
                    ]
                    if valid_imgs:
                        current_image_count += len(valid_imgs)
                        # 이미지 전후 텍스트 컨텍스트
                        context_text = " ".join(current_texts[-2:]) if current_texts else ""
                        context = context_text[-100:] if len(context_text) > 100 else context_text
                        for _ in valid_imgs:
                            current_image_contexts.append(context)

            _flush_section()

        else:
            # 구 에디터 fallback: p, h2, h3, img 순회
            # strong/b는 p 내부에서 소제목 역할 여부를 판단
            all_elements = container.css("p, h2, h3, h4, img")
            for elem in all_elements:
                tag_name = getattr(elem, 'tag', '') or ''
                tag_name = tag_name.lower() if tag_name else ''

                if tag_name in ("h2", "h3", "h4"):
                    text = elem.text.strip() if hasattr(elem, 'text') else ""
                    if text and 3 <= len(text) <= 80:
                        _flush_section()
                        current_heading = text
                        current_heading_tag = tag_name

                elif tag_name == "img":
                    src = elem.attrib.get("src", "")
                    if src and not _is_icon_image(src) and not _is_small_image(elem):
                        current_image_count += 1
                        context_text = " ".join(current_texts[-2:]) if current_texts else ""
                        context = context_text[-100:] if len(context_text) > 100 else context_text
                        current_image_contexts.append(context)

                elif tag_name == "p":
                    # p 내부의 strong/b가 소제목인지 확인
                    text = elem.text.strip() if hasattr(elem, 'text') else ""
                    strong_elems = []
                    try:
                        strong_elems = elem.css("strong, b")
                    except Exception:
                        pass

                    if strong_elems and not text:
                        # p 전체가 strong/b로만 구성된 경우 → 소제목 취급
                        s_text = strong_elems[0].text.strip() if hasattr(strong_elems[0], 'text') else ""
                        if s_text and 5 <= len(s_text) <= 50:
                            _flush_section()
                            current_heading = s_text
                            current_heading_tag = "strong"
                            continue

                    # 일반 본문 텍스트
                    full_text = ""
                    if hasattr(elem, 'get_all_text'):
                        full_text = elem.get_all_text() or ""
                    elif text:
                        full_text = text
                    full_text = full_text.strip()
                    if full_text:
                        current_texts.append(full_text)

            _flush_section()

    except Exception as e:
        logger.debug(f"섹션 추출 오류: {e}")

    return sections


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
                text = (getattr(elem, 'text', '') or '').strip()
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
    result = {
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
    if content.sections:
        result["sections"] = [
            {
                "heading": s.heading,
                "heading_tag": s.heading_tag,
                "text": s.text,
                "char_count": s.char_count,
                "image_count": s.image_count,
                "image_contexts": s.image_contexts,
                "order_index": s.order_index,
            }
            for s in content.sections
        ]
    if content.full_text:
        result["full_text"] = content.full_text[:5000]
    return result
