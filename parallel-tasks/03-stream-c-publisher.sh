#!/bin/bash
# ============================================================
# 03-stream-c-publisher.sh — Stream C: 블로그 발행 모듈
# ============================================================
# 실행: ./parallel-tasks/03-stream-c-publisher.sh
# 조건: Phase 0 완료 후
# 담당: src/publisher/*
# 금지: src/analyzer/*, src/generator/*, src/utils/* 수정 금지
# 소요: 1~2시간
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Stream C: publisher 모듈 개발"
echo "  담당 파일: src/publisher/*"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

claude -p "
SPEC.md 섹션 4.3 (publisher) + 섹션 6 (봇 탐지 우회)을 읽고 블로그 발행 모듈을 구현해줘.

## 범위 (이 파일들만 수정)
- src/publisher/__init__.py
- src/publisher/auth.py
- src/publisher/editor.py
- src/publisher/stealth.py
- src/publisher/scheduler.py

## ⚠️ 절대 수정 금지
- src/analyzer/*, src/generator/*, src/utils/*
- config.py (import만 허용)

## ⚠️ 기술 제약
- Playwright만 사용 (Scrapling 사용 금지 — 발행은 Playwright 전용)
- 네이버 블로그 글쓰기 API는 2020년 종료됨. API 발행 시도 금지.

## 구현 순서

### 1. stealth.py (다른 모듈의 의존성)
\`\`\`python
def human_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
    '''랜덤 딜레이. random.uniform(min_ms/1000, max_ms/1000) sleep'''

def human_typing(page, selector: str, text: str) -> None:
    '''한 글자씩 입력. 글자간 50~200ms. 2% 오타율 (backspace 후 재입력).
    공백 후 10% 확률로 300~800ms 추가 휴지.'''

def random_mouse_movement(page) -> None:
    '''랜덤 좌표로 마우스 이동 (자연스러운 커브)'''

def setup_stealth_browser(playwright) -> 'Browser':
    '''navigator.webdriver 제거, 핑거프린트 랜덤화,
    WebGL/Canvas 노이즈, 실제 User-Agent 설정'''
\`\`\`

### 2. auth.py
- Playwright Chromium 시작 (headless=True)
- 브라우저 설정: user_data_dir, viewport 1920x1080, locale ko-KR, timezone Asia/Seoul
- https://nid.naver.com/nidlogin.login 접속
- ID/PW 입력: pyperclip 클립보드 복사 → Ctrl+V (send_keys 사용 금지!)
- 각 동작 사이 human_delay 적용
- 로그인 성공 확인 (URL 변경 또는 특정 요소)
- 2FA 팝업 감지 시 → Slack 알림 후 대기

### 3. editor.py
동작 순서:
1. 블로그 글쓰기 페이지 이동 (https://blog.naver.com/{blog_id}/postwrite)
2. '작성 중인 글' 팝업 → 취소 클릭 (try/except)
3. '도움말' 팝업 → 닫기 (try/except)
4. 제목 입력: human_typing
5. 본문 입력:
   a. iframe(mainFrame) 진입: page.frame_locator('#mainFrame')
   b. 에디터 영역 포커스
   c. body_html을 단락(<p>) 단위로 분할
   d. 각 단락을 human_typing으로 입력
   e. 이미지 삽입 위치([IMAGE_PLACEHOLDER_N])에서 이미지 업로드
6. 이미지 업로드: 에디터 내 이미지 버튼 → set_input_files()
7. 태그 입력
8. 발행 버튼 클릭 (또는 임시저장)
9. 발행 결과 URL 캡처

에러 처리:
- 각 단계 타임아웃 30초
- 실패 시 스크린샷 저장 (screenshots/ 폴더)
- 부분 실패 시 임시저장 시도

### 4. scheduler.py
- config.py의 PUBLISH_MODES 참조
- generate_publish_time(base_hour_range, jitter_minutes) → datetime
  정각/30분 패턴 회피
- check_daily_limit(blog_id) → bool
  DB에서 당일 발행 건수 확인
- get_min_interval_ok(blog_id) → bool
  마지막 발행 시각과 현재 시각 차이 확인

### 5. __init__.py
- publish_draft(draft_id: str) -> dict 함수 export
- auth → editor → 결과 반환 파이프라인

## 코딩 규칙
- Python 3.11+, 타입 힌트
- Playwright sync API 사용 (async 아님)
- logging 모듈
- 환경변수는 config.py에서

## 검증
python -c 'from src.publisher import publish_draft; print(\"import OK\")'
python -c 'from src.publisher.stealth import human_delay, human_typing; print(\"stealth OK\")'
"
