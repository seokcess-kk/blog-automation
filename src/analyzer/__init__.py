"""
analyzer - 네이버 블로그 상위노출 패턴 분석 모듈

키워드를 입력받아 네이버 검색 상위 블로그들을 분석하고,
상위노출에 필요한 패턴을 추출합니다.

파이프라인:
1. serp_collector: 네이버 검색 → 상위 5개 URL 수집
2. content_parser: 각 URL → 본문 구조 분석
3. pattern_extractor: 분석 결과 → 통합 패턴 추출
"""

import logging
from typing import Any, Optional

from src.analyzer.serp_collector import collect_top_urls
from src.analyzer.content_parser import (
    parse_blog_content,
    ParsedContent,
    content_to_dict,
)
from src.analyzer.pattern_extractor import (
    extract_patterns,
    ExtractedPattern,
    pattern_to_dict,
)

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_keyword",
    "collect_top_urls",
    "parse_blog_content",
    "extract_patterns",
    "ParsedContent",
    "ExtractedPattern",
]


def analyze_keyword(
    keyword: str,
    top_n: int = 5,
    include_raw_data: bool = False,
) -> dict[str, Any]:
    """
    키워드로 상위노출 패턴을 분석합니다.

    전체 파이프라인:
    1. 네이버 검색으로 상위 N개 블로그 URL 수집
    2. 각 블로그 콘텐츠 파싱 및 분석
    3. 통합 패턴 추출

    Args:
        keyword: 분석할 키워드
        top_n: 분석할 상위 블로그 개수 (기본값: 5)
        include_raw_data: 원본 분석 데이터 포함 여부

    Returns:
        분석 결과 딕셔너리:
        {
            "success": bool,
            "keyword": str,
            "pattern": {...},  # 추출된 패턴
            "analyzed_count": int,
            "source_urls": [...],
            "raw_data": [...],  # include_raw_data=True 시
            "error": str | None,
        }

    Example:
        >>> result = analyze_keyword("강남 맛집")
        >>> if result["success"]:
        ...     print(f"평균 글자수: {result['pattern']['avg_char_count']}")
        ...     print(f"평균 이미지: {result['pattern']['avg_image_count']}")
    """
    logger.info(f"키워드 분석 시작: '{keyword}' (top_n={top_n})")

    result: dict[str, Any] = {
        "success": False,
        "keyword": keyword,
        "pattern": None,
        "analyzed_count": 0,
        "source_urls": [],
        "error": None,
    }

    try:
        # Step 1: 상위 URL 수집
        logger.info("Step 1: SERP 수집 중...")
        urls = collect_top_urls(keyword, count=top_n)

        if not urls:
            result["error"] = "검색 결과에서 블로그 URL을 찾을 수 없습니다."
            logger.warning(result["error"])
            return result

        result["source_urls"] = urls
        logger.info(f"수집된 URL: {len(urls)}개")

        # Step 2: 각 URL 콘텐츠 파싱
        logger.info("Step 2: 콘텐츠 파싱 중...")
        parsed_contents: list[ParsedContent] = []

        for url in urls:
            content = parse_blog_content(url, keyword)
            if content:
                parsed_contents.append(content)
            else:
                logger.warning(f"파싱 실패: {url}")

        if not parsed_contents:
            result["error"] = "모든 URL의 콘텐츠 파싱에 실패했습니다."
            logger.warning(result["error"])
            return result

        result["analyzed_count"] = len(parsed_contents)
        logger.info(f"파싱 완료: {len(parsed_contents)}개")

        # Step 3: 패턴 추출
        logger.info("Step 3: 패턴 추출 중...")
        pattern = extract_patterns(parsed_contents, keyword)

        if not pattern:
            result["error"] = "패턴 추출에 실패했습니다."
            logger.warning(result["error"])
            return result

        result["pattern"] = pattern_to_dict(pattern)
        result["success"] = True

        # 원본 데이터 포함 (옵션)
        if include_raw_data:
            result["raw_data"] = [content_to_dict(c) for c in parsed_contents]

        logger.info(
            f"키워드 분석 완료: '{keyword}' - "
            f"avg_chars={pattern.avg_char_count}, "
            f"avg_images={pattern.avg_image_count}, "
            f"avg_headings={pattern.avg_heading_count}"
        )

        return result

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"키워드 분석 오류: {e}")
        return result
