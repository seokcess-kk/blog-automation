"""
stealth.py - 봇 탐지 우회를 위한 휴먼 시뮬레이션 모듈

기능:
- human_delay: 랜덤 딜레이
- human_typing: 한 글자씩 입력 (오타 시뮬레이션 포함)
- random_mouse_movement: 자연스러운 마우스 이동
- setup_stealth_browser: 스텔스 브라우저 설정
"""
import random
import time
import math
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, Browser, Playwright

logger = logging.getLogger(__name__)


def human_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
    """
    랜덤 딜레이를 적용합니다.

    Args:
        min_ms: 최소 딜레이 (밀리초)
        max_ms: 최대 딜레이 (밀리초)
    """
    delay_seconds = random.uniform(min_ms / 1000, max_ms / 1000)
    time.sleep(delay_seconds)


def human_typing(page: "Page", selector: str, text: str) -> None:
    """
    한 글자씩 사람처럼 입력합니다.

    특징:
    - 글자 간 50~200ms 딜레이
    - 2% 확률로 오타 발생 (backspace 후 재입력)
    - 공백 후 10% 확률로 300~800ms 추가 휴지

    Args:
        page: Playwright Page 객체
        selector: 입력할 요소의 선택자
        text: 입력할 텍스트
    """
    from src.config import TYPING_DELAY_MS, TYPO_PROBABILITY

    element = page.locator(selector)
    element.click()
    human_delay(100, 300)  # 클릭 후 짧은 대기

    # 한국어 자음/모음 (오타용)
    korean_chars = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅓㅗㅜㅡㅣ"

    for i, char in enumerate(text):
        # 2% 확률로 오타 발생
        if random.random() < TYPO_PROBABILITY:
            # 랜덤 오타 입력
            typo_char = random.choice(korean_chars) if ord(char) > 127 else random.choice("qwertyuiop")
            page.keyboard.type(typo_char)
            human_delay(50, 150)

            # 오타 인식 후 백스페이스
            human_delay(100, 300)
            page.keyboard.press("Backspace")
            human_delay(50, 150)
            logger.debug(f"오타 시뮬레이션: '{typo_char}' → 삭제 → '{char}'")

        # 실제 문자 입력
        page.keyboard.type(char)

        # 글자 간 딜레이
        delay_ms = random.randint(TYPING_DELAY_MS[0], TYPING_DELAY_MS[1])
        time.sleep(delay_ms / 1000)

        # 공백 후 10% 확률로 추가 휴지 (생각하는 시간)
        if char == " " and random.random() < 0.1:
            human_delay(300, 800)


def random_mouse_movement(page: "Page") -> None:
    """
    랜덤 좌표로 마우스를 자연스럽게 이동합니다.
    베지어 커브를 활용한 부드러운 움직임을 시뮬레이션합니다.

    Args:
        page: Playwright Page 객체
    """
    viewport = page.viewport_size
    if not viewport:
        viewport = {"width": 1920, "height": 1080}

    # 현재 위치 (화면 중앙으로 가정)
    current_x = viewport["width"] // 2
    current_y = viewport["height"] // 2

    # 랜덤 목표 좌표 (화면 내 안전 영역)
    margin = 100
    target_x = random.randint(margin, viewport["width"] - margin)
    target_y = random.randint(margin, viewport["height"] - margin)

    # 베지어 커브를 위한 제어점 (±30% 범위 확장으로 자연스러운 곡선)
    dx = abs(target_x - current_x)
    dy = abs(target_y - current_y)
    offset_x = int(dx * 0.3)
    offset_y = int(dy * 0.3)
    control_x = random.randint(min(current_x, target_x) - offset_x, max(current_x, target_x) + offset_x)
    control_y = random.randint(min(current_y, target_y) - offset_y, max(current_y, target_y) + offset_y)
    # 화면 범위 내로 클램프
    control_x = max(0, min(control_x, viewport["width"]))
    control_y = max(0, min(control_y, viewport["height"]))

    # 10~20 단계로 이동
    steps = random.randint(10, 20)

    for step in range(steps + 1):
        t = step / steps

        # 2차 베지어 커브 계산
        x = (1 - t) ** 2 * current_x + 2 * (1 - t) * t * control_x + t ** 2 * target_x
        y = (1 - t) ** 2 * current_y + 2 * (1 - t) * t * control_y + t ** 2 * target_y

        page.mouse.move(x, y)

        # 각 단계별 미세한 딜레이
        time.sleep(random.uniform(0.01, 0.03))

    logger.debug(f"마우스 이동: ({current_x}, {current_y}) → ({target_x}, {target_y})")


def setup_stealth_browser(playwright: "Playwright", account: str = None) -> "Browser":
    """
    스텔스 브라우저를 설정합니다.

    특징:
    - navigator.webdriver 제거
    - 핑거프린트 랜덤화
    - WebGL/Canvas 노이즈
    - 실제 User-Agent 설정
    - 계정별 세션 분리

    Args:
        playwright: Playwright 인스턴스
        account: 계정 식별자 (A, B 등). None이면 기본 디렉토리 사용

    Returns:
        설정된 Browser 객체
    """
    from pathlib import Path
    from src.config import BROWSER_VIEWPORT, BROWSER_LOCALE, BROWSER_TIMEZONE, USER_DATA_DIR, HEADLESS

    # 실제 크롬 User-Agent 목록
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    selected_user_agent = random.choice(user_agents)

    # 브라우저 시작 인자
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
    ]

    # user_data_dir 경로 설정 (계정별 세션 분리)
    if account:
        user_data_path = str(Path(USER_DATA_DIR) / f"account_{account}")
        Path(user_data_path).mkdir(parents=True, exist_ok=True)
    else:
        user_data_path = str(USER_DATA_DIR)

    browser = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_path,
        headless=HEADLESS,
        args=browser_args,
        viewport=BROWSER_VIEWPORT,
        locale=BROWSER_LOCALE,
        timezone_id=BROWSER_TIMEZONE,
        user_agent=selected_user_agent,
        ignore_https_errors=True,
        java_script_enabled=True,
    )

    # 스텔스 스크립트 주입 (새 페이지마다 적용)
    stealth_script = """
    // navigator.webdriver 제거
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // 플러그인 배열 조작
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // 언어 설정
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ko-KR', 'ko', 'en-US', 'en'],
    });

    // Chrome 객체 추가
    window.chrome = {
        runtime: {},
    };

    // Permission API 조작
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // WebGL 렌더러 랜덤화
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            const gl = thisArg;
            if (param === 37445) {  // UNMASKED_VENDOR_WEBGL
                return 'Google Inc. (NVIDIA)';
            }
            if (param === 37446) {  // UNMASKED_RENDERER_WEBGL
                return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)';
            }
            return target.apply(thisArg, args);
        }
    };

    // Canvas 노이즈 추가
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png') {
            const ctx = this.getContext('2d');
            if (ctx) {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // 미세한 노이즈 추가 (0 또는 1)
                    imageData.data[i] = imageData.data[i] + Math.floor(Math.random() * 2);
                }
                ctx.putImageData(imageData, 0, 0);
            }
        }
        return originalToDataURL.apply(this, arguments);
    };
    """

    # 모든 페이지에 스크립트 적용
    for page in browser.pages:
        page.add_init_script(stealth_script)

    # 새 페이지 생성 시에도 적용
    browser.on("page", lambda page: page.add_init_script(stealth_script))

    logger.info(f"스텔스 브라우저 설정 완료 (User-Agent: {selected_user_agent[:50]}...)")

    return browser


def apply_stealth_to_page(page: "Page") -> None:
    """
    개별 페이지에 스텔스 스크립트를 적용합니다.

    Args:
        page: Playwright Page 객체
    """
    stealth_script = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });
    window.chrome = { runtime: {} };
    """
    page.add_init_script(stealth_script)
    logger.debug("페이지에 스텔스 스크립트 적용 완료")
