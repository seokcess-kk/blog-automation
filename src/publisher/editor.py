"""
editor.py - 네이버 블로그 에디터 자동화 모듈

기능:
- 글쓰기 페이지 이동
- 제목/본문 입력 (human_typing)
- 이미지 업로드
- 태그 입력
- 발행 또는 임시저장
"""
import re
import logging
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from src.publisher.stealth import human_delay, human_typing, random_mouse_movement

if TYPE_CHECKING:
    from playwright.sync_api import Page, FrameLocator

logger = logging.getLogger(__name__)


class BlogEditor:
    """네이버 블로그 에디터 자동화 클래스"""

    def __init__(self, page: "Page", blog_id: str):
        """
        Args:
            page: Playwright Page 객체 (로그인 완료 상태)
            blog_id: 블로그 ID
        """
        self.page = page
        self.blog_id = blog_id
        self.main_frame: Optional["FrameLocator"] = None

    def _go_to_write_page(self) -> None:
        """글쓰기 페이지로 이동합니다."""
        from src.config import NAVER_BLOG_WRITE_URL, STEP_TIMEOUT_SECONDS

        write_url = NAVER_BLOG_WRITE_URL.format(blog_id=self.blog_id)
        logger.info(f"글쓰기 페이지 이동: {write_url}")

        self.page.goto(write_url, wait_until="domcontentloaded")
        human_delay(2000, 3000)

        # mainFrame iframe 대기
        self.page.wait_for_selector("#mainFrame", timeout=STEP_TIMEOUT_SECONDS * 1000)
        self.main_frame = self.page.frame_locator("#mainFrame")
        logger.info("글쓰기 페이지 로드 완료")

    def _dismiss_popups(self) -> None:
        """작성 중인 글 팝업, 도움말 팝업 등을 닫습니다."""
        human_delay(1000, 1500)

        # 작성 중인 글 팝업 (복구/취소)
        try:
            cancel_button = self.main_frame.locator("button:has-text('취소')")
            if cancel_button.count() > 0:
                cancel_button.click()
                logger.info("'작성 중인 글' 팝업 취소")
                human_delay(500, 1000)
        except Exception:
            pass

        # 도움말 팝업 닫기
        try:
            close_selectors = [
                ".se-popup-close-button",
                "button:has-text('닫기')",
                ".se-help-popup-close",
                "[class*='close']",
            ]
            for selector in close_selectors:
                close_button = self.main_frame.locator(selector)
                if close_button.count() > 0:
                    close_button.first.click()
                    logger.info(f"팝업 닫기: {selector}")
                    human_delay(300, 500)
        except Exception:
            pass

    def _enter_title(self, title: str) -> None:
        """
        제목을 입력합니다.

        Args:
            title: 블로그 글 제목
        """
        logger.info(f"제목 입력: {title[:30]}...")

        # 제목 입력 영역 찾기
        title_selectors = [
            ".se-title-text",
            ".se-text-paragraph.se-text-paragraph-align-",
            "[contenteditable='true']",
        ]

        for selector in title_selectors:
            try:
                title_element = self.main_frame.locator(selector).first
                if title_element.count() > 0:
                    title_element.click()
                    human_delay(300, 600)
                    break
            except Exception:
                continue

        # 기존 내용 삭제 후 입력
        self.page.keyboard.press("Control+a")
        human_delay(100, 200)

        # human_typing 대신 한 번에 입력 (제목은 짧음)
        self.page.keyboard.type(title, delay=random_typing_delay())
        human_delay(500, 1000)

        logger.info("제목 입력 완료")

    def _parse_body_into_paragraphs(self, body_html: str) -> List[dict]:
        """
        본문 HTML을 단락 단위로 파싱합니다.

        Args:
            body_html: HTML 형식의 본문

        Returns:
            단락 정보 리스트 [{"type": "text|image", "content": "..."}, ...]
        """
        paragraphs = []

        # HTML 태그 제거 및 단락 분리
        # <p> 태그, <br> 태그, 줄바꿈 기준으로 분리
        text = re.sub(r'<br\s*/?>', '\n', body_html)
        text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text)
        text = re.sub(r'<[^>]+>', '', text)

        # 이미지 플레이스홀더 처리
        pattern = r'\[IMAGE_PLACEHOLDER_(\d+)\]'

        parts = re.split(pattern, text)

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # 숫자만 있으면 이미지 인덱스
            if part.isdigit():
                paragraphs.append({
                    "type": "image",
                    "content": int(part)
                })
            else:
                # 텍스트 단락
                for line in part.split('\n'):
                    line = line.strip()
                    if line:
                        paragraphs.append({
                            "type": "text",
                            "content": line
                        })

        return paragraphs

    def _enter_body(self, body_html: str, images: List[str] = None) -> None:
        """
        본문을 입력합니다.

        Args:
            body_html: HTML 형식의 본문
            images: 이미지 파일 경로 리스트
        """
        from src.config import STEP_TIMEOUT_SECONDS

        images = images or []
        logger.info(f"본문 입력 시작 (이미지 {len(images)}개)")

        # 본문 에디터 영역 포커스
        try:
            body_selectors = [
                ".se-content",
                ".se-component-content",
                ".se-text-paragraph",
                "[contenteditable='true']",
            ]

            for selector in body_selectors:
                body_element = self.main_frame.locator(selector)
                if body_element.count() > 0:
                    body_element.first.click()
                    human_delay(300, 600)
                    break
        except Exception as e:
            logger.warning(f"본문 영역 포커스 실패: {e}")

        # Tab으로 본문 영역으로 이동
        self.page.keyboard.press("Tab")
        human_delay(500, 800)

        # 본문을 단락으로 파싱
        paragraphs = self._parse_body_into_paragraphs(body_html)

        for para in paragraphs:
            random_mouse_movement(self.page)

            if para["type"] == "image":
                # 이미지 삽입
                image_index = para["content"]
                if image_index < len(images):
                    self._insert_image(images[image_index])
            else:
                # 텍스트 입력
                text = para["content"]
                self.page.keyboard.type(text, delay=random_typing_delay())
                human_delay(200, 500)

                # Enter로 줄바꿈
                self.page.keyboard.press("Enter")
                human_delay(100, 300)

            # 가끔 마우스 이동 (자연스러운 행동)
            if len(paragraphs) > 5:
                random_mouse_movement(self.page)

        logger.info("본문 입력 완료")

    def _insert_image(self, image_path: str) -> None:
        """
        이미지를 에디터에 삽입합니다.

        Args:
            image_path: 이미지 파일 경로
        """
        from src.config import STEP_TIMEOUT_SECONDS

        logger.info(f"이미지 삽입: {image_path}")

        try:
            # 이미지 버튼 클릭
            image_button_selectors = [
                ".se-toolbar-item-image",
                "button[data-name='image']",
                ".se-image-button",
            ]

            for selector in image_button_selectors:
                img_btn = self.main_frame.locator(selector)
                if img_btn.count() > 0:
                    img_btn.click()
                    human_delay(500, 1000)
                    break

            # 파일 업로드 input 찾기 및 파일 설정
            file_input = self.main_frame.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.set_input_files(image_path)
                human_delay(2000, 3000)  # 업로드 대기

            logger.info("이미지 삽입 완료")

        except Exception as e:
            logger.warning(f"이미지 삽입 실패: {e}")
            # 실패해도 계속 진행

    def _enter_tags(self, tags: List[str]) -> None:
        """
        태그를 입력합니다.

        Args:
            tags: 태그 리스트
        """
        if not tags:
            return

        logger.info(f"태그 입력: {tags}")

        try:
            # 태그 입력 영역 찾기
            tag_selectors = [
                ".se-tag-input",
                "input[placeholder*='태그']",
                ".tag-input",
            ]

            for selector in tag_selectors:
                tag_input = self.main_frame.locator(selector)
                if tag_input.count() > 0:
                    tag_input.click()
                    human_delay(300, 500)
                    break

            # 각 태그 입력
            for tag in tags:
                self.page.keyboard.type(tag, delay=random_typing_delay())
                human_delay(200, 400)
                self.page.keyboard.press("Enter")
                human_delay(300, 600)

            logger.info("태그 입력 완료")

        except Exception as e:
            logger.warning(f"태그 입력 실패: {e}")

    def _click_publish(self) -> str:
        """
        발행 버튼을 클릭합니다.

        Returns:
            발행된 글 URL
        """
        from src.config import STEP_TIMEOUT_SECONDS

        logger.info("발행 시작")

        try:
            # 발행 버튼 클릭
            publish_selectors = [
                "button:has-text('발행')",
                ".publish_btn__FNb9e",
                ".se-publish-button",
                "#publish-btn",
            ]

            for selector in publish_selectors:
                publish_btn = self.main_frame.locator(selector)
                if publish_btn.count() > 0:
                    publish_btn.click()
                    human_delay(1000, 2000)
                    break

            # 발행 확인 팝업에서 확인 클릭
            confirm_selectors = [
                "button:has-text('확인')",
                "button:has-text('발행하기')",
                ".confirm-button",
            ]

            for selector in confirm_selectors:
                confirm_btn = self.main_frame.locator(selector)
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    human_delay(2000, 3000)
                    break

            # 발행 완료 대기 및 URL 캡처
            self.page.wait_for_load_state("networkidle", timeout=STEP_TIMEOUT_SECONDS * 1000)

            # 발행된 글 URL 추출
            current_url = self.page.url
            if "/postwrite" not in current_url and self.blog_id in current_url:
                logger.info(f"발행 완료: {current_url}")
                return current_url

            # URL에서 포스트 번호 추출 시도
            post_url = self._extract_post_url()
            if post_url:
                return post_url

            return current_url

        except Exception as e:
            logger.error(f"발행 실패: {e}")
            raise

    def _extract_post_url(self) -> Optional[str]:
        """
        발행된 글의 URL을 추출합니다.

        Returns:
            발행된 글 URL 또는 None
        """
        try:
            # 다양한 방법으로 URL 추출 시도
            # 1. 현재 URL에서
            current_url = self.page.url
            if f"blog.naver.com/{self.blog_id}/" in current_url:
                return current_url

            # 2. 성공 메시지에서 링크 추출
            link = self.main_frame.locator("a[href*='blog.naver.com']").first
            if link.count() > 0:
                return link.get_attribute("href")

            return None
        except Exception:
            return None

    def _save_draft(self) -> None:
        """임시저장을 수행합니다."""
        logger.info("임시저장 시도")

        try:
            draft_selectors = [
                "button:has-text('임시저장')",
                ".se-save-button",
                "#save-draft-btn",
            ]

            for selector in draft_selectors:
                draft_btn = self.main_frame.locator(selector)
                if draft_btn.count() > 0:
                    draft_btn.click()
                    human_delay(1000, 2000)
                    logger.info("임시저장 완료")
                    return

        except Exception as e:
            logger.warning(f"임시저장 실패: {e}")

    def _take_screenshot(self, name: str) -> str:
        """
        스크린샷을 저장합니다.

        Args:
            name: 스크린샷 이름

        Returns:
            스크린샷 파일 경로
        """
        from src.config import SCREENSHOTS_DIR

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"{name}_{timestamp}.png"
        self.page.screenshot(path=str(screenshot_path))
        logger.info(f"스크린샷 저장: {screenshot_path}")
        return str(screenshot_path)

    def write_and_publish(
        self,
        title: str,
        body_html: str,
        tags: List[str] = None,
        images: List[str] = None,
        publish: bool = True
    ) -> dict:
        """
        글을 작성하고 발행합니다.

        Args:
            title: 글 제목
            body_html: 본문 HTML
            tags: 태그 리스트
            images: 이미지 파일 경로 리스트
            publish: True면 발행, False면 임시저장

        Returns:
            결과 딕셔너리 {"success": bool, "url": str, "error": str}
        """
        from src.config import SCREENSHOTS_DIR

        tags = tags or []
        images = images or []

        result = {
            "success": False,
            "url": None,
            "error": None,
            "screenshot": None,
        }

        try:
            # 1. 글쓰기 페이지 이동
            self._go_to_write_page()

            # 2. 팝업 닫기
            self._dismiss_popups()

            # 3. 제목 입력
            self._enter_title(title)

            # 4. 본문 입력 (이미지 포함)
            self._enter_body(body_html, images)

            # 5. 태그 입력
            self._enter_tags(tags)

            # 6. 발행 또는 임시저장
            if publish:
                post_url = self._click_publish()
                result["url"] = post_url
            else:
                self._save_draft()
                result["url"] = None

            result["success"] = True
            logger.info(f"글 작성 완료: {title[:30]}...")

        except PlaywrightTimeout as e:
            error_msg = f"타임아웃 오류: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            result["screenshot"] = self._take_screenshot("timeout_error")

            # 부분 실패 시 임시저장 시도
            if publish:
                self._save_draft()

        except Exception as e:
            error_msg = f"작성 오류: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            result["screenshot"] = self._take_screenshot("write_error")

            # 부분 실패 시 임시저장 시도
            if publish:
                try:
                    self._save_draft()
                except Exception:
                    pass

        return result


def random_typing_delay() -> int:
    """랜덤 타이핑 딜레이를 반환합니다 (ms)."""
    import random
    from src.config import TYPING_DELAY_MS
    return random.randint(TYPING_DELAY_MS[0], TYPING_DELAY_MS[1])
