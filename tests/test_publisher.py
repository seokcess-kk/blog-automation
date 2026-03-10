"""
publisher 모듈 테스트.

pytest 실행: pytest tests/test_publisher.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestScheduler:
    """scheduler 모듈 테스트."""

    def test_scheduler_daily_limit(self):
        """일일 발행 한도 체크 테스트."""
        from src.publisher.scheduler import check_daily_limit

        # mock으로 발행 기록 없음 시뮬레이션
        with patch("src.publisher.scheduler._get_today_publish_count") as mock_count:
            mock_count.return_value = 0

            result = check_daily_limit("test_blog")
            assert result is True  # 한도 내

            mock_count.return_value = 10
            result = check_daily_limit("test_blog")
            assert result is False  # 한도 초과

    def test_scheduler_min_interval(self):
        """최소 발행 간격 체크 테스트."""
        from src.publisher.scheduler import get_min_interval_ok

        # mock으로 마지막 발행 시간 시뮬레이션
        with patch("src.publisher.scheduler._get_last_publish_time") as mock_time:
            # 마지막 발행 없음
            mock_time.return_value = None
            result = get_min_interval_ok("test_blog")
            assert result is True

            # 충분한 시간 경과
            mock_time.return_value = datetime.now() - timedelta(hours=5)
            result = get_min_interval_ok("test_blog")
            assert result is True

            # 시간 부족
            mock_time.return_value = datetime.now() - timedelta(minutes=30)
            result = get_min_interval_ok("test_blog")
            assert result is False

    def test_scheduler_publish_time_range(self):
        """발행 시간 범위 테스트."""
        from src.publisher.scheduler import generate_publish_time
        from src.config import PUBLISH_HOUR_RANGE

        # 여러 번 생성하여 범위 내인지 확인
        for _ in range(10):
            publish_time = generate_publish_time()

            if publish_time:
                hour = publish_time.hour
                assert PUBLISH_HOUR_RANGE[0] <= hour < PUBLISH_HOUR_RANGE[1]

    def test_can_publish_now(self):
        """현재 발행 가능 여부 테스트."""
        from src.publisher.scheduler import can_publish_now

        with patch("src.publisher.scheduler.check_daily_limit") as mock_limit:
            with patch("src.publisher.scheduler.get_min_interval_ok") as mock_interval:
                # 둘 다 OK
                mock_limit.return_value = True
                mock_interval.return_value = True

                can, reason = can_publish_now("test_blog")
                assert can is True
                assert reason is None

                # 일일 한도 초과
                mock_limit.return_value = False
                mock_interval.return_value = True

                can, reason = can_publish_now("test_blog")
                assert can is False
                assert "한도" in reason or "limit" in reason.lower()

    def test_get_next_available_time(self):
        """다음 발행 가능 시간 계산 테스트."""
        from src.publisher.scheduler import get_next_available_time

        next_time = get_next_available_time("test_blog")

        # datetime 객체 반환 확인
        assert next_time is None or isinstance(next_time, datetime)


class TestPublishDraft:
    """publish_draft 통합 테스트."""

    def test_publish_draft_returns_correct_structure(self):
        """publish_draft 반환 구조 테스트."""
        from src.publisher import publish_draft

        # mock으로 전체 파이프라인 시뮬레이션
        with patch("src.publisher.can_publish_now") as mock_can:
            mock_can.return_value = (False, "테스트 차단")

            result = publish_draft("test-draft-id")

            assert "success" in result
            assert "draft_id" in result
            assert "error" in result

    def test_publish_draft_error_handling(self):
        """publish_draft 오류 처리 테스트."""
        from src.publisher import publish_draft

        with patch("src.publisher.can_publish_now") as mock_can:
            mock_can.side_effect = Exception("테스트 오류")

            result = publish_draft("test-id")

            assert result["success"] is False
            assert "오류" in result["error"] or "error" in result["error"].lower()


class TestAuth:
    """auth 모듈 테스트."""

    def test_naver_authenticator_exists(self):
        """NaverAuthenticator 클래스 존재 확인."""
        from src.publisher.auth import NaverAuthenticator

        assert NaverAuthenticator is not None

    def test_login_to_naver_function_exists(self):
        """login_to_naver 함수 존재 확인."""
        from src.publisher.auth import login_to_naver

        assert callable(login_to_naver)


class TestEditor:
    """editor 모듈 테스트."""

    def test_blog_editor_exists(self):
        """BlogEditor 클래스 존재 확인."""
        from src.publisher.editor import BlogEditor

        assert BlogEditor is not None

    @pytest.mark.live
    def test_editor_live(self):
        """실제 에디터 테스트 (--live 옵션으로 실행)."""
        # 실제 환경에서만 실행
        pass
