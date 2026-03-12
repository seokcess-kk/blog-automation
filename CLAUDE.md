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
python -m src.cli analyze --keyword "키워드" --brand-url "https://example.com" --brand-name "브랜드명"
python -m src.cli analyze --keyword "키워드" --brand-programs "프로그램1,프로그램2" --brand-location "역삼역 인근"
python -m src.cli generate --keyword-id <uuid>
python -m src.cli publish --draft-id <uuid>
python -m src.cli check-schedule

# 테스트
pytest tests/ -v                         # 전체 테스트
pytest tests/test_analyzer.py -v         # 단일 파일
pytest tests/ -k "test_함수명"            # 단일 테스트
pytest tests/ -m "not live"              # 실제 API 호출 제외 (CI용)
pytest tests/ -m "live"                  # 실제 API 호출만 (환경변수 필수)
# @pytest.mark.live: 네이버 API, Claude API, Supabase 등 외부 서비스 호출 테스트

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

- `src/analyzer/`: SERP 수집 → 콘텐츠 파싱 → 패턴 추출 → Claude Haiku 심층 분석
  - `brand_crawler.py`: 브랜드 홈페이지 크롤링 + Gemini로 정보 추출
  - `deep_analyzer.py`: 상위노출 글 문체/구조/이미지 배치 심층 분석 (Claude Haiku)
- `src/generator/`: 프롬프트 빌드 → Claude API → 이미지 생성
  - `prompt_builder.py`: 패턴 + 브랜드 정보 → 프롬프트 조립
- `src/publisher/`: 인증 → 에디터 조작 → 스케줄링
- `src/utils/`: EXIF 삽입, 의료광고법 검증, 네이버 API

### 데이터 흐름

```
keywords (pending) → analyzer → patterns (DB 저장)
       ↓                  ↓
  brand_url → brand_crawler → brand_info (patterns에 포함)
                  ↓
         deep_analyzer → 심층 분석 (문체/구조/토픽)
                            ↓
patterns + brand_info → generator → drafts (draft)
                            ↓
drafts (draft) → publisher → drafts (published) + publish_logs
```

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

### 브랜드 정보 통합

브랜드 크롤링 → Gemini Flash 분석 → 프롬프트에 주입하여 원고에 브랜드 자연스럽게 통합.

```python
# src/analyzer/brand_crawler.py
@dataclass
class BrandInfo:
    brand_name: str           # 브랜드명 (원고에서 4~5회 언급)
    summary: str              # 한 줄 요약
    programs: list[str]       # 대표 프로그램명 (필수 언급)
    stats: list[str]          # 실적/통계 (신뢰감 형성)
    location: dict[str, str]  # 위치 정보 (지역 키워드 강화)
    team: list[str]           # 의료진/전문가 정보
```

**브랜드 통합 규칙** (`prompts/pattern_injection.md` 지침 12번):
- 브랜드명 최소 4~5회 분산 언급 (도입 1회, 중간 2~3회, 마무리 1회)
- 브랜드 전용 섹션 1개 작성 (■ 형식)
- 대표 프로그램명 반드시 언급
- 실적/통계 숫자로 신뢰감 형성
- 위치 정보 마무리 섹션에 포함

### Claude Haiku 심층 분석

상위노출 블로그 5개를 Claude Haiku로 분석하여 문체, 구조, 이미지 배치 전략 추출.
(한국어 분석 정확도 향상 + API 통일)

```python
# src/analyzer/deep_analyzer.py
# 분석 항목: dominant_tone, common_structure, image_strategy,
#           recommended_sections, writing_guidelines, common_topics
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

## 네이버 SE ONE 에디터 규칙 (enforcement: block)

### DOM 직접 조작 금지

네이버 SE ONE 에디터는 **렌더 DOM과 내부 데이터 모델이 분리**되어 있다.
`querySelector`/`removeChild`/`style` 등으로 DOM을 수정해도 **발행 시 내부 모델 기준으로 HTML이 생성**되므로 변경사항이 무시된다.

**서식 변경은 반드시 에디터 툴바 버튼 클릭 또는 키보드 단축키를 사용할 것.**

### 검증된 셀렉터 (2026-03-11 기준)

| 요소 | 셀렉터 | 활성 상태 |
|------|--------|-----------|
| 취소선 버튼 | `button[data-name="strikethrough"]` | `se-is-selected` 클래스 |
| 굵게 버튼 | `button[data-name="bold"]` | `se-is-selected` 클래스 |
| 제목 영역 | `.se-title-text span` | - |
| 본문 영역 | `.se-component.se-text p` | 제목 영역(`.se-documentTitle`) 제외 필수 |
| 발행 버튼 | `button[class*='publish']` | - |
| 발행 확인 | `button.confirm_btn__WEaBq` | - |

### 서식 문제 대응 패턴

```python
# 1. 본문 영역 클릭 (포커스)
# 2. Ctrl+A 전체 선택
# 3. 툴바 버튼 상태 확인 (se-is-selected)
# 4. 활성 상태면 클릭하여 해제 → 에디터 내부 모델 업데이트
# 5. 비활성 상태면 조작하지 않음 (실수 방지)
```

⚠️ `active`, `is-active`, `aria-pressed` 등은 이 에디터에서 사용하지 않음. 반드시 `se-is-selected`로 체크.

---

## 봇 탐지 우회

- user_data_dir 세션 유지
- 클립보드 우회 로그인 (Pyperclip)
- human_typing: 단락별 타이핑, 랜덤 딜레이
- EXIF 메타데이터 삽입 (카메라 정보, 날짜)
- 발행 간격 준수 (min 2시간 이상)

---

## API 에러 처리

- **Nano Banana Pro (429)**: exponential backoff (10s, 30s, 60s)
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
| drafts | 생성된 원고 (status: draft/published/failed) |
| publish_logs | 발행 이력 로깅 |

---

## n8n 워크플로우

| 워크플로우 | 스케줄 | 기능 |
|------------|--------|------|
| Main Pipeline | 매일 09:00 | 키워드 조회 → 패턴 분석 → 원고 생성 |
| Publish Scheduler | 10분 간격 | 발행 조건 확인 → 자동 발행 (max 재시도 3회) |
| Daily Report | 매일 21:00 | 발행 결과 집계 → Slack 리포트 |

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
