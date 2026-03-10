"""
네이버 검색 API 래퍼

네이버 검색 API(blog 검색)를 호출하여 블로그 검색 결과를 반환합니다.
환경변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
"""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def search_blog(keyword: str, display: int = 5) -> list[dict[str, Any]]:
    """네이버 검색 API (blog 검색) 호출.

    Args:
        keyword: 검색할 키워드
        display: 반환할 검색 결과 수 (기본값: 5, 최대: 100)

    Returns:
        검색 결과 리스트. 각 항목은 다음 키를 포함:
        - title: 블로그 포스트 제목
        - link: 블로그 포스트 URL
        - description: 블로그 포스트 요약
        - bloggername: 블로그 이름
        - postdate: 포스트 작성일 (YYYYMMDD)

    Raises:
        없음. HTTPError 발생 시 로깅 후 빈 리스트 반환.

    Example:
        >>> results = search_blog("맛집 추천", display=3)
        >>> for r in results:
        ...     print(r["title"], r["link"])
    """
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error(
            "NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다."
        )
        return []

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": keyword,
        "display": min(display, 100),  # API 최대값 100
        "sort": "sim",  # 정확도순 정렬
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "description": item.get("description", ""),
                "bloggername": item.get("bloggername", ""),
                "postdate": item.get("postdate", ""),
            })

        logger.info(f"네이버 블로그 검색 완료: keyword='{keyword}', 결과 {len(results)}건")
        return results

    except requests.HTTPError as e:
        logger.error(f"네이버 API HTTP 에러: {e}")
        return []
    except requests.RequestException as e:
        logger.error(f"네이버 API 요청 실패: {e}")
        return []
    except ValueError as e:
        logger.error(f"네이버 API 응답 파싱 실패: {e}")
        return []
