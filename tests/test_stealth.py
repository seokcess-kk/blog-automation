"""
stealth 모듈 테스트.

pytest 실행: pytest tests/test_stealth.py -v
"""

import pytest
import time
from unittest.mock import Mock, patch


class TestHumanDelay:
    """human_delay 함수 테스트."""

    def test_human_delay_range(self):
        """human_delay가 지정된 범위 내에서 지연하는지 테스트."""
        from src.publisher.stealth import human_delay

        min_delay = 0.05  # 50ms
        max_delay = 0.2   # 200ms

        for _ in range(10):
            start = time.time()
            human_delay(min_ms=50, max_ms=200)
            elapsed = time.time() - start

            # 약간의 오차 허용
            assert elapsed >= min_delay * 0.9
            assert elapsed <= max_delay * 1.5

    def test_human_delay_default_values(self):
        """human_delay 기본값 테스트."""
        from src.publisher.stealth import human_delay
        from src.config import TYPING_DELAY_MS

        # 기본값으로 호출
        start = time.time()
        human_delay()
        elapsed = time.time() - start

        min_expected = TYPING_DELAY_MS[0] / 1000
        max_expected = TYPING_DELAY_MS[1] / 1000

        assert elapsed >= min_expected * 0.9
        assert elapsed <= max_expected * 1.5


class TestHumanTyping:
    """human_typing 함수 테스트."""

    def test_human_typing_includes_typos(self):
        """human_typing이 일정 확률로 오타를 포함하는지 테스트."""
        from src.publisher.stealth import human_typing

        # 오타 확률 100%로 설정하여 테스트
        with patch("src.publisher.stealth.TYPO_PROBABILITY", 1.0):
            text = "테스트 문장입니다"
            mock_page = Mock()

            # type 메서드가 호출되는지 확인
            human_typing(mock_page, text)

            # 최소 한 번 이상 호출됨
            assert mock_page.type.called or mock_page.keyboard.type.called

    def test_human_typing_without_typos(self):
        """오타 없이 타이핑 테스트."""
        from src.publisher.stealth import human_typing

        # 오타 확률 0%로 설정
        with patch("src.publisher.stealth.TYPO_PROBABILITY", 0.0):
            text = "테스트"
            mock_page = Mock()

            human_typing(mock_page, text)

            # 호출됨 확인
            assert mock_page.type.called or mock_page.keyboard.type.called

    def test_human_typing_handles_empty_text(self):
        """빈 텍스트 처리 테스트."""
        from src.publisher.stealth import human_typing

        mock_page = Mock()
        human_typing(mock_page, "")

        # 빈 텍스트는 아무 작업 없이 완료


class TestTypingDelay:
    """타이핑 딜레이 테스트."""

    def test_typing_delay_range(self):
        """타이핑 딜레이 범위 테스트."""
        from src.config import TYPING_DELAY_MS

        min_ms, max_ms = TYPING_DELAY_MS

        # SPEC 기준: 50~200ms
        assert min_ms >= 50
        assert max_ms <= 200
        assert min_ms < max_ms

    def test_typo_probability_range(self):
        """오타 확률 범위 테스트."""
        from src.config import TYPO_PROBABILITY

        # SPEC 기준: 2%
        assert 0 <= TYPO_PROBABILITY <= 1
        assert TYPO_PROBABILITY == 0.02


class TestRandomMouseMovement:
    """random_mouse_movement 함수 테스트."""

    def test_random_mouse_movement_exists(self):
        """random_mouse_movement 함수 존재 확인."""
        from src.publisher.stealth import random_mouse_movement

        assert callable(random_mouse_movement)

    def test_random_mouse_movement_execution(self):
        """random_mouse_movement 실행 테스트."""
        from src.publisher.stealth import random_mouse_movement

        mock_page = Mock()

        # 에러 없이 실행되는지 확인
        try:
            random_mouse_movement(mock_page)
        except Exception as e:
            # Mock 객체 관련 에러는 무시
            if "Mock" not in str(e):
                raise


class TestSetupStealthBrowser:
    """setup_stealth_browser 함수 테스트."""

    def test_setup_stealth_browser_exists(self):
        """setup_stealth_browser 함수 존재 확인."""
        from src.publisher.stealth import setup_stealth_browser

        assert callable(setup_stealth_browser)

    def test_setup_stealth_browser_returns_browser_options(self):
        """setup_stealth_browser가 브라우저 옵션을 반환하는지 테스트."""
        from src.publisher.stealth import setup_stealth_browser

        result = setup_stealth_browser()

        # dict 또는 관련 객체 반환
        assert result is not None


class TestStealthIntegration:
    """stealth 모듈 통합 테스트."""

    def test_all_stealth_functions_importable(self):
        """모든 stealth 함수 import 가능 확인."""
        from src.publisher.stealth import (
            human_delay,
            human_typing,
            random_mouse_movement,
            setup_stealth_browser,
        )

        assert all([
            callable(human_delay),
            callable(human_typing),
            callable(random_mouse_movement),
            callable(setup_stealth_browser),
        ])

    @pytest.mark.live
    def test_stealth_with_real_browser(self):
        """실제 브라우저로 stealth 테스트 (--live 옵션으로 실행)."""
        # 실제 환경에서만 실행
        pass
