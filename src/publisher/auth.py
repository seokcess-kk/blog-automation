"""
auth.py - 네이버 블로그 인증 모듈

기능:
- 네이버 로그인 (Pyperclip 클립보드 우회)
- 세션 유지 (user_data_dir)
- 2FA 감지 및 Slack 알림
"""
import logging
import requests
from typing import Optional, TYPE_CHECKING

import pyperclip
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from src.publisher.stealth import (
    setup_stealth_browser,
    human_delay,
    random_mouse_movement,
)

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext

logger = logging.getLogger(__name__)


class NaverAuthenticator:
    """네이버 인증 처리 클래스"""

    def __init__(self, username: str, password: str, blog_id: str, account: str = None):
        """
        Args:
            username: 네이버 ID
            password: 네이버 비밀번호
            blog_id: 블로그 ID
            account: 계정 식별자 (A, B 등). 세션 분리에 사용
        """
        self.username = username
        self.password = password
        self.blog_id = blog_id
        self.account = account
        self.browser: Optional["BrowserContext"] = None
        self.page: Optional["Page"] = None
        self._playwright = None

    def _paste_text(self, text: str) -> None:
        """
        클립보드에 텍스트를 복사한 후 Ctrl+V로 붙여넣기합니다.
        send_keys 사용 금지 (봇 탐지 우회)

        Args:
            text: 붙여넣을 텍스트
        """
        pyperclip.copy(text)
        human_delay(100, 300)
        self.page.keyboard.press("Control+v")
        human_delay(200, 500)

    def _check_login_success(self) -> bool:
        """
        로그인 성공 여부를 확인합니다.

        Returns:
            로그인 성공 여부
        """
        try:
            # URL이 로그인 페이지가 아니면 성공
            current_url = self.page.url
            if "nidlogin" not in current_url and "naver.com" in current_url:
                return True

            # 로그인 후 프로필 요소 확인
            self.page.wait_for_selector(".MyView-module__my_area___M1gPh", timeout=5000)
            return True
        except PlaywrightTimeout:
            return False

    def _check_2fa_popup(self) -> bool:
        """
        2FA 팝업 여부를 확인합니다.

        Returns:
            2FA 팝업 표시 여부
        """
        try:
            # 2차 인증 관련 요소 확인
            selectors = [
                "text=2단계 인증",
                "text=본인확인",
                "text=인증번호",
                "#otp",
                ".second_auth",
            ]
            for selector in selectors:
                if self.page.locator(selector).count() > 0:
                    return True
            return False
        except Exception:
            return False

    def _send_slack_notification(self, message: str) -> None:
        """
        Slack 알림을 전송합니다.

        Args:
            message: 알림 메시지
        """
        from src.config import SLACK_WEBHOOK_URL

        if not SLACK_WEBHOOK_URL:
            logger.warning("Slack Webhook URL이 설정되지 않았습니다.")
            return

        try:
            payload = {
                "text": f":warning: 네이버 로그인 알림\n{message}",
                "username": "Blog Automation Bot",
                "icon_emoji": ":robot_face:",
            }
            response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Slack 알림 전송 완료")
            else:
                logger.warning(f"Slack 알림 전송 실패: {response.status_code}")
        except Exception as e:
            logger.error(f"Slack 알림 전송 오류: {e}")

    def login(self) -> bool:
        """
        네이버에 로그인합니다.

        Returns:
            로그인 성공 여부

        Raises:
            Exception: 로그인 실패 시
        """
        from src.config import NAVER_LOGIN_URL, SCREENSHOTS_DIR, STEP_TIMEOUT_SECONDS

        logger.info(f"네이버 로그인 시작: {self.username}")

        try:
            self._playwright = sync_playwright().start()
            self.browser = setup_stealth_browser(self._playwright, account=self.account)

            # 기존 페이지 사용 또는 새 페이지 생성
            if self.browser.pages:
                self.page = self.browser.pages[0]
            else:
                self.page = self.browser.new_page()

            # 로그인 페이지 접속
            self.page.goto(NAVER_LOGIN_URL, wait_until="domcontentloaded")
            human_delay(1000, 2000)

            # 이미 로그인된 상태인지 확인
            if self._check_login_success():
                logger.info("이미 로그인된 상태입니다.")
                return True

            # 랜덤 마우스 이동 (자연스러운 행동)
            random_mouse_movement(self.page)
            human_delay(500, 1000)

            # ID 입력 필드 클릭 및 입력
            id_selector = "#id"
            self.page.click(id_selector)
            human_delay(300, 600)
            self._paste_text(self.username)
            human_delay(500, 1000)

            # 랜덤 마우스 이동
            random_mouse_movement(self.page)

            # PW 입력 필드 클릭 및 입력
            pw_selector = "#pw"
            self.page.click(pw_selector)
            human_delay(300, 600)
            self._paste_text(self.password)
            human_delay(500, 1000)

            # 로그인 버튼 클릭
            login_button = "#log\\.login"
            self.page.click(login_button)
            human_delay(2000, 3000)

            # 2FA 팝업 확인
            if self._check_2fa_popup():
                logger.warning("2FA 인증이 필요합니다!")
                self._send_slack_notification(
                    f"계정 `{self.username}`에서 2FA 인증이 필요합니다.\n"
                    "수동으로 인증을 완료해주세요."
                )

                # 최대 5분간 대기 (사용자가 수동 인증)
                logger.info("2FA 인증 대기 중... (최대 5분)")
                try:
                    self.page.wait_for_url(
                        lambda url: "nidlogin" not in url,
                        timeout=300000  # 5분
                    )
                except PlaywrightTimeout:
                    raise Exception("2FA 인증 타임아웃")

            # 로그인 성공 확인
            self.page.wait_for_load_state("networkidle", timeout=STEP_TIMEOUT_SECONDS * 1000)

            if self._check_login_success():
                logger.info("네이버 로그인 성공!")
                return True

            # 로그인 실패 - 스크린샷 저장
            screenshot_path = SCREENSHOTS_DIR / f"login_failed_{self.username}.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.error(f"로그인 실패. 스크린샷 저장: {screenshot_path}")
            raise Exception("로그인 확인 실패")

        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            if self.page:
                screenshot_path = SCREENSHOTS_DIR / f"login_error_{self.username}.png"
                try:
                    self.page.screenshot(path=str(screenshot_path))
                except Exception:
                    pass
            raise

    def get_page(self) -> "Page":
        """
        현재 페이지 객체를 반환합니다.

        Returns:
            Playwright Page 객체
        """
        if not self.page:
            raise Exception("로그인이 먼저 필요합니다.")
        return self.page

    def get_browser(self) -> "BrowserContext":
        """
        현재 브라우저 컨텍스트를 반환합니다.

        Returns:
            BrowserContext 객체
        """
        if not self.browser:
            raise Exception("로그인이 먼저 필요합니다.")
        return self.browser

    def close(self) -> None:
        """브라우저 리소스를 정리합니다."""
        try:
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
            logger.info("브라우저 리소스 정리 완료")
        except Exception as e:
            logger.warning(f"브라우저 정리 중 오류: {e}")


def login_to_naver(
    username: str,
    password: str,
    blog_id: str,
    account: str = None
) -> NaverAuthenticator:
    """
    네이버에 로그인하고 인증 객체를 반환합니다.

    Args:
        username: 네이버 ID
        password: 네이버 비밀번호
        blog_id: 블로그 ID
        account: 계정 식별자 (A, B 등). 세션 분리에 사용

    Returns:
        NaverAuthenticator 객체
    """
    authenticator = NaverAuthenticator(username, password, blog_id, account=account)
    authenticator.login()
    return authenticator
