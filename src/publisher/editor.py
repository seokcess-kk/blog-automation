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

        # 글쓰기 URL로 직접 이동
        write_url = NAVER_BLOG_WRITE_URL.format(blog_id=self.blog_id)
        logger.info(f"글쓰기 페이지 이동: {write_url}")

        self.page.goto(write_url, wait_until="domcontentloaded")
        human_delay(2000, 3000)

        # 로그인 페이지로 리디렉션되었는지 확인
        current_url = self.page.url
        logger.info(f"현재 URL: {current_url}")

        if "nidlogin" in current_url:
            logger.error("세션이 만료되어 로그인 페이지로 리디렉션되었습니다.")
            self._take_screenshot("session_expired_write")
            raise Exception("세션 만료: 로그인이 필요합니다. 수동 로그인 후 다시 시도하세요.")

        # 새 SE 에디터는 iframe 없이 직접 로드됨
        # 제목 입력 영역이 나타날 때까지 대기
        editor_selectors = [
            ".se-title-text",
            "[placeholder='제목']",
            ".editor-title",
            "#editor-title",
        ]

        editor_found = False
        for selector in editor_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=STEP_TIMEOUT_SECONDS * 1000)
                editor_found = True
                logger.info(f"에디터 로드 완료 (selector: {selector})")
                break
            except Exception:
                continue

        if not editor_found:
            # iframe 방식 폴백 (구버전 에디터)
            try:
                self.page.wait_for_selector("#mainFrame", timeout=5000)
                self.main_frame = self.page.frame_locator("#mainFrame")
                logger.info("구버전 에디터 (iframe) 감지")
            except Exception:
                # 스크린샷 저장 후 진행
                self._take_screenshot("editor_not_found")
                logger.warning(f"에디터 로드 확인 실패. 현재 URL: {self.page.url}")

        logger.info("글쓰기 페이지 로드 완료")

    def _get_locator(self, selector: str):
        """main_frame 또는 page에서 locator를 반환합니다."""
        if self.main_frame:
            return self.main_frame.locator(selector)
        return self.page.locator(selector)

    def _dismiss_popups(self) -> None:
        """작성 중인 글 팝업, 도움말 팝업 등을 닫습니다."""
        human_delay(1000, 1500)

        # 작성 중인 글 팝업 (복구/취소)
        try:
            cancel_button = self._get_locator("button:has-text('취소')")
            if cancel_button.count() > 0:
                cancel_button.click()
                logger.info("'작성 중인 글' 팝업 취소")
                human_delay(500, 1000)
        except Exception:
            pass

        # 우측 도움말 패널 닫기 (X 버튼) - 스크린샷에서 확인된 구조
        try:
            close_selectors = [
                # 우측 도움말 패널 닫기 버튼 (스크린샷 기준)
                "button[class*='close']",
                "svg[class*='close']",
                ".help_panel button",
                "[aria-label='닫기']",
                "[aria-label='close']",
                # 기존 셀렉터
                "button.close_button__mfPSJ",
                ".se-popup-close-button",
                "button:has-text('닫기')",
                ".se-help-popup-close",
            ]
            for selector in close_selectors:
                try:
                    close_button = self._get_locator(selector)
                    if close_button.count() > 0:
                        close_button.first.click()
                        logger.info(f"팝업/패널 닫기: {selector}")
                        human_delay(300, 500)
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # ESC 키로 팝업 닫기 시도
        try:
            self.page.keyboard.press("Escape")
            human_delay(300, 500)
            logger.info("ESC 키로 팝업 닫기 시도")
        except Exception:
            pass

        # 에디터 영역 클릭하여 포커스
        try:
            editor_area = self._get_locator(".se-content, .editor-content, [class*='editor']").first
            if editor_area.count() > 0:
                editor_area.click()
                human_delay(200, 400)
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
            ".se-title-text span",  # 새 SE 에디터
            ".se-title-text",
            "[placeholder='제목']",
        ]

        for selector in title_selectors:
            try:
                title_element = self._get_locator(selector).first
                if title_element.count() > 0:
                    title_element.click()
                    human_delay(300, 600)
                    logger.info(f"제목 영역 클릭: {selector}")
                    break
            except Exception:
                continue

        # 기존 내용 삭제 후 입력
        self.page.keyboard.press("Control+a")
        human_delay(100, 200)

        # 제목만 입력 (짧으므로 한 번에)
        self.page.keyboard.type(title, delay=random_typing_delay())
        human_delay(500, 1000)

        logger.info("제목 입력 완료")
        # 본문 이동은 _enter_body에서 처리

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
        본문을 입력합니다. HTML 서식을 유지하여 입력합니다.

        Args:
            body_html: HTML 형식의 본문
            images: 이미지 파일 경로 리스트
        """
        from src.config import STEP_TIMEOUT_SECONDS
        import pyperclip

        images = images or []
        logger.info(f"본문 입력 시작 (이미지 {len(images)}개)")

        # 본문 에디터 영역으로 명시적 이동 (제목 영역에서 벗어나기)
        body_clicked = False

        # 본문 영역 셀렉터 (우선순위 순)
        body_selectors = [
            ".se-component.se-text p",
            ".se-text-paragraph span",
            ".se-text-paragraph",
            ".se-main-container .se-component-content",
            ".se-component-content",
        ]

        for selector in body_selectors:
            try:
                body_element = self._get_locator(selector)
                elements = body_element.all()
                for elem in elements:
                    try:
                        parent_class = elem.evaluate("el => el.closest('.se-documentTitle') ? 'title' : 'body'")
                        if parent_class == 'title':
                            continue
                    except Exception:
                        pass

                    elem.click()
                    human_delay(500, 800)
                    logger.info(f"본문 영역 클릭: {selector}")
                    body_clicked = True
                    break

                if body_clicked:
                    break
            except Exception as e:
                logger.debug(f"본문 영역 시도 실패 ({selector}): {e}")
                continue

        if not body_clicked:
            try:
                self.page.mouse.click(700, 400)
                human_delay(500, 800)
                body_clicked = True
            except Exception as e:
                logger.warning(f"본문 좌표 클릭 실패: {e}")

        # HTML을 구조화된 형식으로 입력
        # 이미지 플레이스홀더 처리 및 이미지 삽입
        self._enter_body_with_structure(body_html, images)

    def _reset_text_formatting(self) -> None:
        """
        텍스트 서식을 초기화합니다. 특히 취소선 서식을 해제합니다.

        네이버 에디터에서 이전 글의 서식이 남아있거나,
        알 수 없는 이유로 취소선이 활성화되는 문제를 해결합니다.
        """
        logger.info("텍스트 서식 초기화 시작")

        try:
            # 취소선 버튼 셀렉터 (네이버 스마트에디터)
            strikethrough_selectors = [
                "button[data-name='strikethrough']",
                "button[data-command-name='strikethrough']",
                "button.se-toolbar-button-strikethrough",
                "[class*='strikethrough']",
                "button[title*='취소선']",
                "button[aria-label*='취소선']",
            ]

            # 1. 취소선 버튼 상태 확인 및 비활성화
            for selector in strikethrough_selectors:
                try:
                    btn = self._get_locator(selector)
                    if btn.count() > 0:
                        # 버튼의 활성화 상태 확인 (aria-pressed 또는 클래스)
                        is_active = self.page.evaluate(f'''() => {{
                            const btn = document.querySelector("{selector}");
                            if (!btn) return false;

                            // aria-pressed 속성 확인
                            if (btn.getAttribute('aria-pressed') === 'true') return true;

                            // 활성화 클래스 확인
                            if (btn.classList.contains('active') ||
                                btn.classList.contains('se-toolbar-button-active') ||
                                btn.classList.contains('is-active') ||
                                btn.classList.contains('selected')) return true;

                            // 배경색으로 확인
                            const style = window.getComputedStyle(btn);
                            const bg = style.backgroundColor;
                            if (bg && bg !== 'transparent' &&
                                bg !== 'rgba(0, 0, 0, 0)' &&
                                bg !== 'rgb(255, 255, 255)') {{
                                // 배경색이 있으면 활성화 상태일 수 있음
                                return true;
                            }}

                            return false;
                        }}''')

                        if is_active:
                            btn.first.click()
                            human_delay(100, 200)
                            logger.info(f"취소선 버튼 비활성화: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"취소선 버튼 확인 실패 ({selector}): {e}")
                    continue

            # 2. 테스트 입력으로 취소선 상태 재확인
            self.page.keyboard.type("a")
            human_delay(50, 100)

            has_strikethrough = self.page.evaluate('''() => {
                // 방금 입력된 텍스트 요소 찾기
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    let node = selection.anchorNode;
                    // 텍스트 노드인 경우 부모 요소 확인
                    if (node.nodeType === Node.TEXT_NODE) {
                        node = node.parentElement;
                    }

                    while (node && node.tagName !== 'BODY') {
                        const style = window.getComputedStyle(node);
                        const decoration = style.textDecoration || style.textDecorationLine || '';
                        if (decoration.includes('line-through')) {
                            return true;
                        }
                        // strike 또는 s 태그 확인
                        if (node.tagName === 'STRIKE' || node.tagName === 'S' || node.tagName === 'DEL') {
                            return true;
                        }
                        node = node.parentElement;
                    }
                }
                return false;
            }''')

            # 입력한 문자 삭제
            self.page.keyboard.press("Backspace")
            human_delay(50, 100)

            if has_strikethrough:
                logger.warning("취소선이 여전히 활성화됨 - 강제 해제 시도")

                # 모든 취소선 버튼 클릭 시도
                for selector in strikethrough_selectors:
                    try:
                        btn = self._get_locator(selector)
                        if btn.count() > 0:
                            btn.first.click()
                            human_delay(100, 200)
                            logger.info(f"취소선 강제 클릭: {selector}")

                            # 다시 테스트
                            self.page.keyboard.type("b")
                            human_delay(50, 100)

                            still_has_strike = self.page.evaluate('''() => {
                                const selection = window.getSelection();
                                if (selection.rangeCount > 0) {
                                    let node = selection.anchorNode;
                                    if (node.nodeType === Node.TEXT_NODE) {
                                        node = node.parentElement;
                                    }
                                    while (node && node.tagName !== 'BODY') {
                                        const style = window.getComputedStyle(node);
                                        const decoration = style.textDecoration || style.textDecorationLine || '';
                                        if (decoration.includes('line-through')) {
                                            return true;
                                        }
                                        if (node.tagName === 'STRIKE' || node.tagName === 'S' || node.tagName === 'DEL') {
                                            return true;
                                        }
                                        node = node.parentElement;
                                    }
                                }
                                return false;
                            }''')

                            self.page.keyboard.press("Backspace")
                            human_delay(50, 100)

                            if not still_has_strike:
                                logger.info("취소선 해제 성공")
                                break
                    except Exception:
                        continue

            logger.info("텍스트 서식 초기화 완료")

        except Exception as e:
            logger.warning(f"텍스트 서식 초기화 실패: {e}")

    def _enter_body_with_structure(self, body_html: str, images: List[str]) -> None:
        """
        HTML 구조를 유지하면서 본문을 입력합니다.
        소제목(H2, H3)과 단락을 구분하여 입력합니다.
        """
        import pyperclip
        from bs4 import BeautifulSoup

        logger.info("구조화된 본문 입력 시작")

        # 서식 초기화 - 취소선 강제 해제
        self._reset_text_formatting()

        # HTML 파싱
        soup = BeautifulSoup(body_html, 'html.parser')

        # 이미지 인덱스 추적
        image_index = 0

        # 모든 요소 순회 (find_all 사용)
        elements = soup.find_all(['p', 'h2', 'h3', 'ul', 'ol'])

        for element in elements:
            if element.name == 'h2':
                # H2 소제목 - 빈 줄로 구분 (굵게 처리 제거)
                text = element.get_text().strip()
                if text:
                    self.page.keyboard.press("Enter")
                    human_delay(100, 200)
                    self._type_text(text)
                    self.page.keyboard.press("Enter")
                    self.page.keyboard.press("Enter")  # 빈 줄로 구분
                    human_delay(200, 400)
                    logger.info(f"소제목 입력 (H2): {text[:30]}...")

            elif element.name == 'h3':
                # H3 소제목 - 빈 줄로 구분 (굵게 처리 제거)
                text = element.get_text().strip()
                if text:
                    self.page.keyboard.press("Enter")
                    human_delay(100, 200)
                    self._type_text(text)
                    self.page.keyboard.press("Enter")
                    self.page.keyboard.press("Enter")  # 빈 줄로 구분
                    human_delay(200, 400)
                    logger.info(f"소제목 입력 (H3): {text[:30]}...")

            elif element.name == 'p':
                # 단락 처리
                text = element.get_text().strip()
                if not text:
                    continue

                # 이미지 플레이스홀더 확인
                if '[IMAGE_PLACEHOLDER_' in text:
                    import re
                    match = re.search(r'\[IMAGE_PLACEHOLDER_(\d+)\]', text)
                    if match and int(match.group(1)) < len(images):
                        self._insert_image(images[int(match.group(1))])
                    continue

                # 일반 텍스트 단락
                self._type_text(text)
                self.page.keyboard.press("Enter")
                human_delay(150, 350)

            elif element.name in ['ul', 'ol']:
                # 목록 처리
                self._enter_list(element)

            human_delay(100, 200)

        logger.info("구조화된 본문 입력 완료")

    def _enter_heading(self, text: str, level: int = 2) -> None:
        """
        소제목을 입력합니다. 에디터의 제목 스타일을 적용합니다.
        """
        logger.info(f"소제목 입력 (H{level}): {text[:30]}...")

        # 빈 줄 추가
        self.page.keyboard.press("Enter")
        human_delay(200, 400)

        # 소제목 텍스트 입력
        self.page.keyboard.type(text, delay=random_typing_delay())
        human_delay(300, 500)

        # 텍스트 선택
        self.page.keyboard.press("Control+a")
        human_delay(100, 200)

        # 제목 스타일 적용 시도 (에디터 툴바 사용)
        try:
            # 본문/제목 드롭다운 클릭
            style_dropdown = self._get_locator("button.se-toolbar-item-headline, [class*='headline'], .se-text-style-button")
            if style_dropdown.count() > 0:
                style_dropdown.first.click()
                human_delay(300, 500)

                # 제목2 또는 제목3 선택
                heading_option = self._get_locator(f"[data-value='heading{level}'], button:has-text('제목{level}')")
                if heading_option.count() > 0:
                    heading_option.first.click()
                    human_delay(200, 400)
                    logger.info(f"제목{level} 스타일 적용 완료")
                else:
                    # 대안: 굵게 처리
                    self.page.keyboard.press("Control+b")
                    logger.info("제목 스타일 대신 굵게 적용")
        except Exception as e:
            # 스타일 적용 실패시 굵게만 처리
            self.page.keyboard.press("Control+b")
            logger.debug(f"제목 스타일 적용 실패, 굵게 적용: {e}")

        # 선택 해제 및 다음 줄로
        self.page.keyboard.press("End")
        self.page.keyboard.press("Enter")
        human_delay(200, 400)

    def _enter_paragraph(self, element, images: List[str], current_image_index: int) -> None:
        """
        단락을 입력합니다. 강조(<strong>) 등의 인라인 서식을 처리합니다.
        """
        # 이미지 플레이스홀더 확인
        text = str(element)
        import re
        placeholder_match = re.search(r'\[IMAGE_PLACEHOLDER_(\d+)\]', text)

        if placeholder_match:
            # 이미지 삽입
            img_idx = int(placeholder_match.group(1))
            if img_idx < len(images):
                self._insert_image(images[img_idx])
            return

        # 일반 텍스트 단락
        plain_text = element.get_text().strip()
        if not plain_text:
            return

        # 강조 텍스트 처리
        has_strong = element.find('strong') is not None

        if has_strong:
            # 강조가 있는 경우: 전체 입력 후 강조 부분 처리
            self._type_text(plain_text)
        else:
            self._type_text(plain_text)

        # 줄바꿈
        self.page.keyboard.press("Enter")
        human_delay(100, 300)

    def _enter_list(self, element) -> None:
        """
        목록(ul, ol)을 입력합니다.
        """
        is_ordered = element.name == 'ol'
        items = element.find_all('li')

        for i, item in enumerate(items):
            text = item.get_text().strip()
            if is_ordered:
                prefix = f"{i+1}. "
            else:
                prefix = "• "

            self.page.keyboard.type(prefix + text, delay=random_typing_delay())
            self.page.keyboard.press("Enter")
            human_delay(100, 300)

    def _type_text(self, text: str) -> None:
        """
        텍스트를 입력합니다. 긴 텍스트는 클립보드를 사용합니다.
        """
        import pyperclip

        if len(text) > 100:
            # 긴 텍스트는 클립보드로 붙여넣기
            pyperclip.copy(text)
            human_delay(100, 200)
            self.page.keyboard.press("Control+v")
            human_delay(300, 500)
        else:
            # 짧은 텍스트는 직접 타이핑
            self.page.keyboard.type(text, delay=random_typing_delay())
            human_delay(200, 400)

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
                img_btn = self._get_locator(selector)
                if img_btn.count() > 0:
                    img_btn.click()
                    human_delay(500, 1000)
                    break

            # 파일 업로드 input 찾기 및 파일 설정
            file_input = self._get_locator("input[type='file']")
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
                tag_input = self._get_locator(selector)
                if tag_input.count() > 0:
                    tag_input.click()
                    human_delay(300, 500)
                    logger.info(f"태그 영역 클릭: {selector}")
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
        from src.config import STEP_TIMEOUT_SECONDS, SCREENSHOTS_DIR

        logger.info("발행 시작")

        try:
            # 발행 전 스크린샷
            self._take_screenshot("before_publish")
            logger.info(f"발행 전 URL: {self.page.url}")

            # 1단계: 우측 상단 "발행" 버튼 클릭 (발행 설정 팝업 열기)
            publish_selectors = [
                "button.publish_btn__FNb9e",  # 새 에디터 발행 버튼
                "button.se-publish-btn",
                "button:has-text('발행')",
                ".se-publish-button",
                "#publish-btn",
                "button[class*='publish']",
            ]

            publish_clicked = False
            for selector in publish_selectors:
                try:
                    publish_btn = self._get_locator(selector)
                    if publish_btn.count() > 0:
                        publish_btn.first.click()
                        logger.info(f"발행 버튼 클릭: {selector}")
                        publish_clicked = True
                        human_delay(1500, 2500)
                        break
                except Exception as e:
                    logger.debug(f"발행 버튼 시도 실패 ({selector}): {e}")
                    continue

            if not publish_clicked:
                self._take_screenshot("publish_btn_not_found")
                raise Exception("발행 버튼을 찾을 수 없습니다")

            # 발행 설정 팝업 스크린샷
            self._take_screenshot("publish_popup")

            # 2단계: 발행 설정 팝업에서 최종 "발행" 또는 "발행하기" 버튼 클릭
            confirm_selectors = [
                "button.confirm_btn__WEaBq",  # 새 에디터 발행 확인 버튼
                "button.se-popup-button-confirm",
                "button:has-text('발행하기')",
                ".popup-publish-button",
                "button.btn_publish",
                "button[class*='confirm']",
            ]

            human_delay(500, 1000)
            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    confirm_btn = self._get_locator(selector)
                    if confirm_btn.count() > 0:
                        confirm_btn.first.click()
                        logger.info(f"발행 확인 클릭: {selector}")
                        confirm_clicked = True
                        human_delay(3000, 5000)
                        break
                except Exception as e:
                    logger.debug(f"발행 확인 버튼 시도 실패 ({selector}): {e}")
                    continue

            if not confirm_clicked:
                # 팝업이 없을 수 있음 - 바로 발행되는 경우
                logger.warning("발행 확인 버튼을 찾을 수 없음 (바로 발행되었을 수 있음)")

            # 발행 완료 대기
            self.page.wait_for_load_state("networkidle", timeout=STEP_TIMEOUT_SECONDS * 1000)

            # 발행 후 스크린샷
            self._take_screenshot("after_publish")

            # 발행된 글 URL 추출
            current_url = self.page.url
            logger.info(f"발행 후 URL: {current_url}")

            # 로그인 페이지로 리디렉션된 경우 - 세션 만료
            if "nidlogin" in current_url:
                self._take_screenshot("session_expired")
                raise Exception("세션이 만료되어 로그인 페이지로 리디렉션되었습니다")

            # 발행 성공 URL 확인
            if self.blog_id in current_url and "/postwrite" not in current_url:
                logger.info(f"발행 완료: {current_url}")
                return current_url

            # URL에서 포스트 번호 추출 시도
            post_url = self._extract_post_url()
            if post_url:
                logger.info(f"추출된 포스트 URL: {post_url}")
                return post_url

            # 글쓰기 페이지에 아직 있는 경우 - 발행 실패 가능성
            if "/PostWriteForm" in current_url or "postwrite" in current_url.lower():
                self._take_screenshot("still_on_write_page")
                raise Exception("발행 후에도 글쓰기 페이지에 있습니다. 발행이 실패했을 수 있습니다.")

            return current_url

        except Exception as e:
            logger.error(f"발행 실패: {e}")
            self._take_screenshot("publish_error")
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
            link = self._get_locator("a[href*='blog.naver.com']").first
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
                draft_btn = self._get_locator(selector)
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
