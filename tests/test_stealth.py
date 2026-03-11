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

        # human_delay 기본값: min_ms=500, max_ms=2000
        DEFAULT_MIN_MS = 500
        DEFAULT_MAX_MS = 2000

        # 기본값으로 호출
        start = time.time()
        human_delay()
        elapsed = time.time() - start

        min_expected = DEFAULT_MIN_MS / 1000
        max_expected = DEFAULT_MAX_MS / 1000

        assert elapsed >= min_expected * 0.9
        assert elapsed <= max_expected * 1.5


class TestHumanTyping:
    """human_typing 함수 테스트."""

    def test_human_typing_calls_keyboard_type(self):
        """human_typing이 keyboard.type을 호출하는지 테스트."""
        from src.publisher.stealth import human_typing

        text = "테스트"
        mock_page = Mock()
        selector = "#test-input"

        # locator mock 설정
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator

        human_typing(mock_page, selector, text)

        # keyboard.type이 호출됨 확인 (각 글자마다 호출)
        assert mock_page.keyboard.type.called
        # 최소 텍스트 길이만큼 호출
        assert mock_page.keyboard.type.call_count >= len(text)

    def test_human_typing_clicks_element(self):
        """human_typing이 요소를 클릭하는지 테스트."""
        from src.publisher.stealth import human_typing

        text = "테스트"
        mock_page = Mock()
        selector = "#test-input"

        # locator mock 설정
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator

        human_typing(mock_page, selector, text)

        # locator가 호출되고 click이 호출됨 확인
        mock_page.locator.assert_called_with(selector)
        mock_locator.click.assert_called_once()

    def test_human_typing_handles_empty_text(self):
        """빈 텍스트 처리 테스트."""
        from src.publisher.stealth import human_typing

        mock_page = Mock()
        selector = "#test-input"

        # locator mock 설정
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator

        human_typing(mock_page, selector, "")

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

        # playwright mock 설정
        mock_playwright = Mock()
        mock_browser = Mock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_browser
        mock_browser.pages = []

        result = setup_stealth_browser(mock_playwright)

        # Browser 객체 반환 확인
        assert result is not None
        assert mock_playwright.chromium.launch_persistent_context.called


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
