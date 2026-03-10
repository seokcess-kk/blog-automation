# Playwright Guidelines

> **enforcement: suggest**
> Playwright 라이브러리 사용 가이드라인 (쓰기 작업/발행)

---

## 1. 핵심 원칙

```
Scrapling = 읽기 전용 (크롤링, 데이터 수집)
Playwright = 쓰기 작업 (에디터 조작, 발행)
```

**두 라이브러리의 역할을 절대 혼용하지 말 것.**

---

## 2. 브라우저 설정

### 2.1 기본 설정 (봇 탐지 우회)

```python
from playwright.sync_api import sync_playwright

def create_browser():
    """봇 탐지 우회 브라우저 생성"""
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch_persistent_context(
        user_data_dir="./browser_data",  # 세션 유지
        headless=False,  # 봇 탐지 우회
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )

    return browser
```

### 2.2 user_data_dir 세션 유지

```python
# 첫 실행: 수동 로그인 후 세션 저장
# 이후 실행: 자동으로 로그인 상태 유지

USER_DATA_DIR = "./browser_data/naver_session"
```

---

## 3. 네이버 로그인

### 3.1 클립보드 우회 로그인 (Pyperclip)

```python
import pyperclip
from playwright.sync_api import Page

def naver_login(page: Page, username: str, password: str):
    """클립보드 우회 로그인 (키 입력 탐지 회피)"""
    page.goto("https://nid.naver.com/nidlogin.login")

    # ID 입력 (클립보드)
    pyperclip.copy(username)
    page.click("#id")
    page.keyboard.press("Control+v")
    human_delay(500, 1000)

    # PW 입력 (클립보드)
    pyperclip.copy(password)
    page.click("#pw")
    page.keyboard.press("Control+v")
    human_delay(500, 1000)

    # 로그인 버튼
    page.click(".btn_login")
    page.wait_for_load_state("networkidle")
```

### 3.2 세션 확인

```python
def is_logged_in(page: Page) -> bool:
    """로그인 상태 확인"""
    page.goto("https://blog.naver.com")
    return page.locator(".my_menu").count() > 0
```

---

## 4. Human-like 타이핑

### 4.1 딜레이 함수

```python
import random
import time

def human_delay(min_ms: int = 50, max_ms: int = 200):
    """인간적인 랜덤 딜레이"""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

def human_typing(page: Page, selector: str, text: str, typo_prob: float = 0.02):
    """인간적인 타이핑 (오타 포함)"""
    element = page.locator(selector)
    element.click()

    for char in text:
        # 2% 확률로 오타
        if random.random() < typo_prob:
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            page.keyboard.type(wrong_char)
            human_delay(100, 200)
            page.keyboard.press("Backspace")
            human_delay(50, 100)

        page.keyboard.type(char)
        human_delay(50, 200)
```

### 4.2 단락별 타이핑

```python
def type_paragraphs(page: Page, paragraphs: list[str]):
    """단락별로 나눠서 타이핑 (봇 탐지 우회)"""
    for i, para in enumerate(paragraphs):
        human_typing(page, ".se-text-paragraph", para)
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")

        # 단락 간 긴 휴식
        human_delay(500, 1500)

        # 5단락마다 더 긴 휴식
        if (i + 1) % 5 == 0:
            human_delay(2000, 4000)
```

---

## 5. 네이버 스마트에디터 조작

### 5.1 에디터 iframe 진입

```python
def enter_editor(page: Page):
    """스마트에디터 iframe 진입"""
    page.goto("https://blog.naver.com/PostWriteForm.naver")
    page.wait_for_selector("iframe#mainFrame")

    # mainFrame 진입
    main_frame = page.frame("mainFrame")
    main_frame.wait_for_selector(".se-content")

    return main_frame
```

### 5.2 제목 입력

```python
def set_title(frame, title: str):
    """제목 입력"""
    frame.click(".se-title-text")
    human_typing(frame, ".se-title-text", title)
```

### 5.3 본문 입력

```python
def set_body(frame, paragraphs: list[str]):
    """본문 입력 (단락별)"""
    frame.click(".se-content")

    for para in paragraphs:
        human_typing(frame, ".se-text-paragraph", para)
        frame.keyboard.press("Enter")
        frame.keyboard.press("Enter")
        human_delay(500, 1500)
```

### 5.4 이미지 업로드

```python
def upload_image(frame, image_path: str):
    """이미지 업로드"""
    # 이미지 버튼 클릭
    frame.click(".se-image-toolbar-button")
    human_delay(300, 500)

    # 파일 선택
    with frame.expect_file_chooser() as fc_info:
        frame.click(".se-upload-button")
    file_chooser = fc_info.value
    file_chooser.set_files(image_path)

    # 업로드 완료 대기
    frame.wait_for_selector(".se-image-resource")
    human_delay(1000, 2000)
```

### 5.5 태그 입력

```python
def set_tags(frame, tags: list[str]):
    """태그 입력"""
    for tag in tags:
        frame.click(".tag_post_area input")
        human_typing(frame, ".tag_post_area input", tag)
        frame.keyboard.press("Enter")
        human_delay(200, 400)
```

### 5.6 발행

```python
def publish(frame) -> str:
    """발행 및 URL 반환"""
    # 발행 버튼
    frame.click(".publish_btn")
    human_delay(500, 1000)

    # 확인 버튼
    frame.click(".confirm_btn")

    # 발행 완료 대기
    frame.wait_for_url("**/PostView.naver**")

    return frame.url
```

---

## 6. 봇 탐지 우회 설정

### 6.1 config.py 설정값

```python
PUBLISH_MODES = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal":       {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive":   {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}

PUBLISH_HOUR_RANGE = (9, 18)      # 발행 허용 시간
TYPING_DELAY_MS = (50, 200)       # 타이핑 딜레이
TYPO_PROBABILITY = 0.02           # 오타 확률 2%
MAX_RETRY_COUNT = 3               # 최대 재시도
```

### 6.2 핑거프린트 랜덤화

```python
def randomize_fingerprint(browser):
    """브라우저 핑거프린트 랜덤화"""
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
    ]

    browser.set_viewport_size(random.choice(viewports))
```

---

## 7. 에러 처리

### 7.1 재시도 패턴

```python
def publish_with_retry(draft_id: str, max_retries: int = 3) -> bool:
    """발행 재시도"""
    for attempt in range(max_retries):
        try:
            publish(draft_id)
            return True
        except Exception as e:
            log_error(draft_id, e)
            if attempt < max_retries - 1:
                time.sleep(60 * (attempt + 1))  # 1분, 2분, 3분
    return False
```

### 7.2 일반적인 에러

| 에러 | 원인 | 해결책 |
|------|------|--------|
| TimeoutError | 요소 로딩 지연 | wait_for_selector 타임아웃 증가 |
| ElementNotFound | iframe 미진입 | frame() 확인 |
| LoginRequired | 세션 만료 | user_data_dir 재로그인 |
| CaptchaDetected | 캡차 발생 | 수동 해결 후 재시도 |

---

## 8. 주의사항

### 8.1 절대 하지 말 것

- Playwright로 대량 크롤링 시도
- headless=True로 발행 시도 (탐지됨)
- 세션 공유 (user_data_dir 분리)

→ **크롤링은 반드시 Scrapling 사용**

### 8.2 발행 제한

- **하루 5개 초과 금지**
- 최소 발행 간격: 2시간
- 발행 시간: 09:00 ~ 18:00
- 의료 키워드: conservative 모드 권장

---

## 9. 참고 자료

- [Playwright Python 문서](https://playwright.dev/python/)
- [네이버 에디터 구조](./resources/naver-editor.md)
