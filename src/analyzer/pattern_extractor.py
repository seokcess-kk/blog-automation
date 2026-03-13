"""
상위노출 패턴 추출 모듈.

여러 블로그 콘텐츠 분석 결과를 종합하여 통합 패턴을 추출합니다.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from src.analyzer.content_parser import ParsedContent, content_to_dict

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPattern:
    """추출된 상위노출 패턴."""

    avg_char_count: int
    """평균 글자 수"""

    avg_image_count: int
    """평균 이미지 개수"""

    avg_heading_count: int
    """평균 소제목 개수"""

    title_patterns: list[str]
    """제목 패턴 (공통 구조)"""

    keyword_placement: dict[str, Any]
    """키워드 배치 패턴"""

    related_keywords: list[str]
    """공통 연관 키워드"""

    content_structure: dict[str, Any]
    """콘텐츠 구조 패턴"""

    image_position_pattern: dict[str, Any]
    """이미지 배치 패턴"""

    source_count: int
    """분석에 사용된 소스 개수"""

    source_urls: list[str]
    """분석된 URL 목록"""

    source_titles: list[str]
    """분석된 블로그 제목 목록"""


def extract_patterns(
    contents: list[ParsedContent],
    keyword: str,
) -> Optional[ExtractedPattern]:
    """
    여러 콘텐츠 분석 결과에서 통합 패턴을 추출합니다.

    Args:
        contents: 파싱된 콘텐츠 목록
        keyword: 분석 대상 키워드

    Returns:
        추출된 패턴 또는 None (데이터 부족 시)

    Example:
        >>> pattern = extract_patterns(parsed_contents, "맛집")
        >>> print(pattern.avg_char_count, pattern.avg_image_count)
    """
    if not contents:
        logger.warning("패턴 추출 실패: 분석할 콘텐츠가 없습니다.")
        return None

    logger.info(f"패턴 추출 시작: {len(contents)}개 콘텐츠 분석")

    # 평균 계산
    avg_char_count = _calculate_average([c.char_count for c in contents])
    avg_image_count = _calculate_average([c.image_count for c in contents])
    avg_heading_count = _calculate_average([c.heading_count for c in contents])

    # 제목 패턴 추출
    title_patterns = _extract_title_patterns([c.title for c in contents], keyword)

    # 키워드 배치 패턴
    keyword_placement = _analyze_keyword_placement(contents)

    # 연관 키워드 교집합
    related_keywords = _find_common_keywords(contents)

    # 콘텐츠 구조 분석
    content_structure = _analyze_content_structure(contents)

    # 이미지 배치 패턴
    image_position_pattern = _analyze_image_positions(contents)

    pattern = ExtractedPattern(
        avg_char_count=avg_char_count,
        avg_image_count=avg_image_count,
        avg_heading_count=avg_heading_count,
        title_patterns=title_patterns,
        keyword_placement=keyword_placement,
        related_keywords=related_keywords,
        content_structure=content_structure,
        image_position_pattern=image_position_pattern,
        source_count=len(contents),
        source_urls=[c.url for c in contents],
        source_titles=[c.title for c in contents],
    )

    logger.info(
        f"패턴 추출 완료: "
        f"avg_chars={avg_char_count}, avg_images={avg_image_count}, "
        f"avg_headings={avg_heading_count}"
    )

    return pattern


def _calculate_average(values: list[int]) -> int:
    """정수 평균 계산."""
    if not values:
        return 0
    return round(sum(values) / len(values))


def _extract_title_patterns(titles: list[str], keyword: str) -> list[str]:
    """
    제목에서 공통 패턴을 추출합니다.

    패턴 종류:
    - 키워드 위치 (앞/중간/뒤)
    - 공통 접두사/접미사
    - 제목 길이 패턴
    """
    patterns = []

    if not titles:
        return patterns

    keyword_lower = keyword.lower()

    # 키워드 위치 분석
    keyword_positions = {"front": 0, "middle": 0, "end": 0, "none": 0}

    for title in titles:
        title_lower = title.lower()
        if keyword_lower not in title_lower:
            keyword_positions["none"] += 1
            continue

        pos = title_lower.find(keyword_lower)
        relative_pos = pos / max(len(title), 1)

        if relative_pos < 0.3:
            keyword_positions["front"] += 1
        elif relative_pos > 0.7:
            keyword_positions["end"] += 1
        else:
            keyword_positions["middle"] += 1

    # 가장 빈번한 위치 패턴
    most_common_pos = max(keyword_positions.items(), key=lambda x: x[1])
    if most_common_pos[1] > 0:
        patterns.append(f"keyword_position:{most_common_pos[0]}")

    # 제목 길이 패턴
    lengths = [len(t) for t in titles]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    patterns.append(f"avg_title_length:{round(avg_length)}")

    # 공통 접미사 패턴 (정보성 콘텐츠에 적합한 것만)
    # 후기/리뷰/추천은 정보성 원칙 위반이므로 제외
    _NON_INFORMATIONAL_SUFFIXES = {"후기", "리뷰", "추천", "체험", "경험"}
    suffix_candidates = ["정리", "비교", "TOP", "BEST", "가이드", "방법", "총정리"]
    for suffix in suffix_candidates:
        count = sum(1 for t in titles if suffix in t)
        if count >= len(titles) / 2:  # 50% 이상에서 발견
            patterns.append(f"common_suffix:{suffix}")

    # 후기/리뷰 패턴이 발견되면 로그 경고 (생성 시 정보성으로 전환)
    for non_info_suffix in _NON_INFORMATIONAL_SUFFIXES:
        count = sum(1 for t in titles if non_info_suffix in t)
        if count >= len(titles) / 2:
            logger.info(
                f"상위글에 '{non_info_suffix}' 패턴 빈출({count}/{len(titles)}) "
                f"→ 정보성 원칙에 따라 패턴에서 제외"
            )

    # 숫자 포함 패턴 (예: "TOP 5", "10가지")
    number_count = sum(1 for t in titles if re.search(r'\d+', t))
    if number_count >= len(titles) / 2:
        patterns.append("includes_number")

    return patterns


def _analyze_keyword_placement(contents: list[ParsedContent]) -> dict[str, Any]:
    """키워드 배치 패턴을 분석합니다."""
    result = {
        "in_title_ratio": 0.0,
        "avg_keyword_count": 0,
        "first_occurrence_ratio": [],  # 첫 등장 위치 비율
        "distribution": "unknown",
    }

    if not contents:
        return result

    # 제목 포함 비율
    title_count = sum(1 for c in contents if c.keyword_in_title)
    result["in_title_ratio"] = round(title_count / len(contents), 2)

    # 평균 키워드 출현 횟수
    keyword_counts = [len(c.keyword_positions) for c in contents]
    result["avg_keyword_count"] = _calculate_average(keyword_counts)

    # 첫 등장 위치 비율 분석
    first_positions = []
    for content in contents:
        if content.keyword_positions and content.char_count > 0:
            first_pos = content.keyword_positions[0]
            ratio = first_pos / content.char_count
            first_positions.append(round(ratio, 2))

    if first_positions:
        avg_first_pos = sum(first_positions) / len(first_positions)
        result["first_occurrence_ratio"] = round(avg_first_pos, 2)

        # 분포 패턴 결정
        if avg_first_pos < 0.1:
            result["distribution"] = "front_heavy"
        elif avg_first_pos < 0.3:
            result["distribution"] = "balanced_front"
        else:
            result["distribution"] = "spread_out"

    return result


def _find_common_keywords(contents: list[ParsedContent]) -> list[str]:
    """
    콘텐츠들의 공통 연관 키워드를 추출합니다.

    여러 콘텐츠에서 반복적으로 등장하는 키워드를 찾습니다.
    """
    if not contents:
        return []

    # 모든 연관 키워드 수집
    all_keywords: Counter = Counter()

    for content in contents:
        for kw in content.related_keywords:
            all_keywords[kw] += 1

    # 소표본(3개 이하) 시 min_occurrence 보정
    min_occurrence = 2 if len(contents) <= 3 else max(2, len(contents) // 2)
    common_keywords = [
        kw for kw, count in all_keywords.most_common(20)
        if count >= min_occurrence
    ]

    return common_keywords[:10]


def _analyze_content_structure(contents: list[ParsedContent]) -> dict[str, Any]:
    """콘텐츠 구조 패턴을 분석합니다."""
    result = {
        "has_list_ratio": 0.0,
        "has_table_ratio": 0.0,
        "common_headings": [],
        "heading_styles": [],
    }

    if not contents:
        return result

    # 목록/테이블 사용 비율
    list_count = sum(1 for c in contents if c.has_list)
    table_count = sum(1 for c in contents if c.has_table)

    result["has_list_ratio"] = round(list_count / len(contents), 2)
    result["has_table_ratio"] = round(table_count / len(contents), 2)

    # 공통 소제목 패턴
    all_headings: Counter = Counter()
    for content in contents:
        for heading in content.headings:
            # 소제목 정규화 (숫자, 기호 제거)
            normalized = re.sub(r'[\d\.\-\)\(\s]+', '', heading)
            if len(normalized) >= 2:
                all_headings[normalized] += 1

    # 2개 이상에서 발견되는 소제목
    common_headings = [
        h for h, count in all_headings.most_common(10)
        if count >= 2
    ]
    result["common_headings"] = common_headings

    return result


def _analyze_image_positions(contents: list[ParsedContent]) -> dict[str, Any]:
    """이미지 배치 패턴을 분석합니다."""
    result = {
        "pattern": "unknown",
        "avg_first_image_position": 0.0,
        "images_per_1000_chars": 0.0,
    }

    if not contents:
        return result

    # 첫 이미지 위치 분석
    first_positions = []
    for content in contents:
        if content.image_positions:
            first_positions.append(content.image_positions[0])

    if first_positions:
        avg_first = sum(first_positions) / len(first_positions)
        result["avg_first_image_position"] = round(avg_first, 2)

        # 패턴 결정
        if avg_first < 0.1:
            result["pattern"] = "image_first"
        elif avg_first < 0.3:
            result["pattern"] = "early_images"
        else:
            result["pattern"] = "distributed"

    # 글자 당 이미지 비율
    total_chars = sum(c.char_count for c in contents)
    total_images = sum(c.image_count for c in contents)

    if total_chars > 0:
        ratio = (total_images / total_chars) * 1000
        result["images_per_1000_chars"] = round(ratio, 2)

    return result


def pattern_to_dict(pattern: ExtractedPattern) -> dict[str, Any]:
    """ExtractedPattern을 딕셔너리로 변환합니다."""
    return {
        "avg_char_count": pattern.avg_char_count,
        "avg_image_count": pattern.avg_image_count,
        "avg_heading_count": pattern.avg_heading_count,
        "title_patterns": pattern.title_patterns,
        "keyword_placement": pattern.keyword_placement,
        "related_keywords": pattern.related_keywords,
        "content_structure": pattern.content_structure,
        "image_position_pattern": pattern.image_position_pattern,
        "source_count": pattern.source_count,
        "source_urls": pattern.source_urls,
        "source_titles": pattern.source_titles,
    }
