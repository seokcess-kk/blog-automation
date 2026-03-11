# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

네이버 블로그 상위노출 패턴을 역분석하여 SEO 최적화된 콘텐츠를 자동 생성하고 발행하는 파이프라인.

```
키워드 → 상위노출 분석(Scrapling) → 원고 생성(Claude API) → 이미지(Nano Banana Pro) + EXIF → 발행(Playwright)
```

---

## 빌드 및 실행 명령어

```bash
# 환경 설정
python -m venv venv
venv\Scripts\activate                    # Windows
source venv/bin/activate                 # Linux/Mac
pip install -r requirements.txt
playwright install chromium

# CLI 실행
python -m src.cli analyze --keyword "키워드"
python -m src.cli generate --keyword-id <uuid>
python -m src.cli publish --draft-id <uuid>
python -m src.cli check-schedule

# 테스트
pytest tests/ -v                         # 전체 테스트
pytest tests/test_analyzer.py -v         # 단일 파일
pytest tests/ -k "test_함수명"            # 단일 테스트
pytest tests/ -m "not live"              # 실제 API 호출 제외
pytest tests/ -m "live"                  # 실제 API 호출만 (환경변수 필요)

# Docker
docker-compose up -d
```

---

## 아키텍처

### 라이브러리 역할 분리 (필수)

| 라이브러리 | 역할 | 용도 |
|-----------|------|------|
| **Scrapling** (StealthyFetcher) | 읽기 전용 | 크롤링, 데이터 수집 |
| **Playwright** (raw) | 쓰기 작업 | 에디터 조작, 발행 |

**두 라이브러리의 역할을 절대 혼용하지 말 것.**

### 모듈 구조

- `src/analyzer/`: SERP 수집 → 콘텐츠 파싱 → 패턴 추출
- `src/generator/`: 프롬프트 빌드 → Claude API → 이미지 생성
- `src/publisher/`: 인증 → 에디터 조작 → 스케줄링
- `src/utils/`: EXIF 삽입, 의료광고법 검증, 네이버 API

### 이미지 생성 (Nano Banana Pro)

```python
from google import genai

client = genai.Client(api_key=GOOGLE_AI_API_KEY)
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt_text,
    config=genai.types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
    ),
)
# 이미지 추출 후 exif.inject_exif() 적용
```

---

## 발행 모드

```python
PUBLISH_MODES = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal":       {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive":   {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}
```

- 하루 5개 초과 금지
- 의료 키워드는 conservative 권장
- 발행 시간대: 09:00 ~ 18:00
- 타이핑 딜레이: 50~200ms, 오타 확률: 2%

---

## 의료광고법 준수 (enforcement: block)

| severity | 카테고리 |
|----------|----------|
| **critical** | 치료효과 오인, 거짓/과장 표현, 비교/비방, 법적 근거 없는 자격 |
| warning | 부작용 정보 누락, 기사/전문가 위장, 인증/보증 부당 사용, 소비자 유인 |

**critical 위반 시 작업 중단. 수동 검수 필수.**

```
원고 생성 → medical_ad_checker.check_violations(text)
→ critical? → Claude 재요청 (max 2회) → 여전히 위반 → 수동 검수 + Slack 알림
```

---

## 봇 탐지 우회

- user_data_dir 세션 유지
- 클립보드 우회 로그인 (Pyperclip)
- human_typing: 단락별 타이핑, 랜덤 딜레이
- EXIF 메타데이터 삽입 (카메라 정보, 날짜)
- 발행 간격 준수 (min 2시간 이상)

---

## API 에러 처리

- **Nano Banana Pro 429**: exponential backoff (10s, 30s, 60s)
- **Safety filter**: 프롬프트 수정 후 재시도 (max 3회)
- **발행 실패**: 자동 재스케줄 (max 3회)

---

## 환경변수

```bash
SUPABASE_URL=
SUPABASE_KEY=
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=              # Nano Banana Pro
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
BLOG_A_USERNAME=
BLOG_A_PASSWORD=
BLOG_B_USERNAME=
BLOG_B_PASSWORD=
SLACK_WEBHOOK_URL=
PUBLISH_MODE=conservative       # conservative|normal|aggressive
HEADLESS=false                  # 봇 탐지 우회를 위해 기본 false
```

---

## DB 테이블 (Supabase)

| 테이블 | 용도 |
|--------|------|
| keywords | 키워드 관리 (status: pending/analyzing/done) |
| patterns | 상위노출 패턴 데이터 |
| drafts | 생성된 원고 (status: ready/published/failed) |
| publish_logs | 발행 이력 로깅 |

---

## 코딩 컨벤션

- Python 3.11+ 타입 힌트 필수
- async/await 패턴 사용
- JSON 구조화 출력 (Claude API)
- 종료코드: 0=성공, 1=실패
- CLI 출력은 `output_json()` 함수로 JSON stdout

---

## Claude Code Skills (enforcement)

| Skill | Enforcement | 설명 |
|-------|-------------|------|
| scrapling-guidelines | suggest | 크롤링 가이드라인 |
| playwright-guidelines | suggest | 발행 자동화 가이드라인 |
| naver-seo | suggest | SEO 최적화 규칙 |
| medical-ad-law | **block** | 위반 시 작업 중단 |
