"""
네이버 검색광고 API 래퍼.

키워드 도구 API를 사용하여 검색량, 경쟁강도 등을 조회합니다.
환경변수: NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY
"""

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Optional

import requests

from src.config import (
    NAVER_AD_CUSTOMER_ID,
    NAVER_AD_ACCESS_LICENSE,
    NAVER_AD_SECRET_KEY,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.searchad.naver.com"


def _generate_signature(timestamp: str, method: str, uri: str) -> str:
    """
    API 요청용 HMAC-SHA256 시그니처를 생성합니다.

    Args:
        timestamp: Unix timestamp (밀리초)
        method: HTTP 메서드 (GET, POST 등)
        uri: API 엔드포인트 경로

    Returns:
        Base64 인코딩된 시그니처
    """
    message = f"{timestamp}.{method}.{uri}"
    signature = hmac.new(
        NAVER_AD_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature).decode("utf-8")


def _get_headers(method: str, uri: str) -> dict[str, str]:
    """
    API 요청 헤더를 생성합니다.

    Args:
        method: HTTP 메서드
        uri: API 엔드포인트 경로

    Returns:
        요청 헤더 딕셔너리
    """
    timestamp = str(int(time.time() * 1000))
    signature = _generate_signature(timestamp, method, uri)

    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": NAVER_AD_ACCESS_LICENSE,
        "X-Customer": NAVER_AD_CUSTOMER_ID,
        "X-Signature": signature,
    }


def get_keyword_stats(
    keywords: list[str],
    show_detail: bool = True,
) -> list[dict[str, Any]]:
    """
    키워드 검색량 및 경쟁강도를 조회합니다.

    Args:
        keywords: 조회할 키워드 리스트 (최대 5개)
        show_detail: 상세 정보 포함 여부

    Returns:
        키워드별 통계 리스트. 각 항목은 다음 키를 포함:
        - relKeyword: 키워드
        - monthlyPcQcCnt: 월간 PC 검색량
        - monthlyMobileQcCnt: 월간 모바일 검색량
        - monthlyAvePcClkCnt: 월간 PC 평균 클릭수
        - monthlyAveMobileClkCnt: 월간 모바일 평균 클릭수
        - monthlyAvePcCtr: 월간 PC 평균 클릭률
        - monthlyAveMobileCtr: 월간 모바일 평균 클릭률
        - compIdx: 경쟁강도 (높음/중간/낮음)

    Example:
        >>> stats = get_keyword_stats(["강남 피부과", "홍대 맛집"])
        >>> for s in stats:
        ...     print(s["relKeyword"], s["monthlyMobileQcCnt"])
    """
    if not NAVER_AD_CUSTOMER_ID or not NAVER_AD_ACCESS_LICENSE or not NAVER_AD_SECRET_KEY:
        logger.error(
            "네이버 검색광고 API 환경변수가 설정되지 않았습니다. "
            "(NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY)"
        )
        return []

    if not keywords:
        return []

    # 최대 5개까지만 허용
    keywords = keywords[:5]

    uri = "/keywordstool"
    method = "GET"

    params = {
        "hintKeywords": ",".join(keywords),
        "showDetail": "1" if show_detail else "0",
    }

    try:
        headers = _get_headers(method, uri)
        response = requests.get(
            f"{BASE_URL}{uri}",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        keyword_list = data.get("keywordList", [])

        logger.info(f"키워드 통계 조회 완료: {keywords}, 결과 {len(keyword_list)}건")
        return keyword_list

    except requests.HTTPError as e:
        logger.error(f"네이버 검색광고 API HTTP 에러: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"응답 내용: {e.response.text}")
        return []
    except requests.RequestException as e:
        logger.error(f"네이버 검색광고 API 요청 실패: {e}")
        return []
    except ValueError as e:
        logger.error(f"네이버 검색광고 API 응답 파싱 실패: {e}")
        return []


def get_related_keywords(
    keyword: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    연관 키워드를 조회합니다.

    Args:
        keyword: 기준 키워드
        limit: 반환할 최대 연관 키워드 수

    Returns:
        연관 키워드 리스트 (검색량 순)
    """
    stats = get_keyword_stats([keyword])

    # 검색량 기준 정렬
    sorted_stats = sorted(
        stats,
        key=lambda x: (
            _parse_search_count(x.get("monthlyMobileQcCnt", 0)) +
            _parse_search_count(x.get("monthlyPcQcCnt", 0))
        ),
        reverse=True,
    )

    return sorted_stats[:limit]


def _parse_search_count(value: Any) -> int:
    """
    검색량 값을 정수로 파싱합니다.

    네이버 API는 검색량이 적을 때 "< 10" 같은 문자열을 반환합니다.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value.startswith("<"):
            return 0
        try:
            return int(value.replace(",", ""))
        except ValueError:
            return 0
    return 0


def get_keyword_competition(keyword: str) -> Optional[str]:
    """
    키워드의 경쟁강도를 조회합니다.

    Args:
        keyword: 조회할 키워드

    Returns:
        경쟁강도 ("높음", "중간", "낮음") 또는 None
    """
    stats = get_keyword_stats([keyword])

    for stat in stats:
        if stat.get("relKeyword") == keyword:
            return stat.get("compIdx")

    return None
