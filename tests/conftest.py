"""
pytest 설정 파일.

테스트 실행 시 프로젝트 루트를 Python 경로에 추가합니다.
"""

import sys
from pathlib import Path

import pytest

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """pytest 마커 등록."""
    config.addinivalue_line(
        "markers",
        "live: 실제 API 호출이 필요한 테스트. --live 옵션으로 실행."
    )
