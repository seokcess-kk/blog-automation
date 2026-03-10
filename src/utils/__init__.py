"""
src.utils - 유틸리티 모듈

이 패키지는 다음 유틸리티를 제공합니다:
- naver_api: 네이버 검색 API 래퍼
- exif: AI 이미지에 카메라 EXIF 메타데이터 삽입
- medical_ad_checker: 의료광고법 위반 표현 검증
"""

from src.utils.naver_api import search_blog
from src.utils.exif import inject_exif, CAMERAS
from src.utils.medical_ad_checker import (
    Violation,
    check_violations,
    has_critical,
    get_violation_summary,
)

__all__ = [
    "search_blog",
    "inject_exif",
    "CAMERAS",
    "Violation",
    "check_violations",
    "has_critical",
    "get_violation_summary",
]
