# CLAUDE.md — blog-automation

> 네이버 블로그 자동화 파이프라인 프로젝트 메모리
> 키워드 분석 → 상위노출 패턴 역분석 → 원고 생성 → 자동 발행

---

## 1. 프로젝트 개요

네이버 블로그 상위노출 패턴을 역분석하여 SEO 최적화된 콘텐츠를 자동 생성하고, 봇 탐지를 우회하여 자동 발행하는 end-to-end 파이프라인.

### 핵심 파이프라인
```
키워드 입력 → 상위노출 패턴 분석(Scrapling) → 원고 생성(Claude API) → 이미지 생성(Nano Banana Pro) + EXIF 삽입 → 자동 발행(Playwright) → 결과 로깅
```

---

## 2. 기술 스택

| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 언어 | Python | 3.11+ | 타입 힌트 필수, async/await |
| 오케스트레이션 | n8n | latest (Docker) | VPS 셀프호스팅, Execute Command |
| 크롤링/분석 | Scrapling | 0.3+ | StealthyFetcher, Adaptive 셀렉터 |
| 발행 자동화 | Playwright | latest | Python sync API, iframe/타이핑 |
| 콘텐츠 생성 | Claude API | claude-sonnet-4-20250514 | JSON 구조화 출력 |
| 이미지 생성 | Nano Banana Pro | gemini-3-pro-image-preview | Google AI Studio API |
| 이미지 처리 | Pillow + piexif | latest | EXIF 메타데이터 삽입 |
| DB | Supabase (PostgreSQL) | Free tier | REST API로 n8n 연동 |
| 알림 | Slack 또는 Telegram | - | n8n 네이티브 노드 |
| 서버 | VPS (Ubuntu 22.04+) | 2vCPU/4GB RAM | Docker Compose |

---

## 3. 프로젝트 구조

```
blog-automation/
├── CLAUDE.md                          # 프로젝트 기억
├── SPEC.md                            # 주문서
├── docker-compose.yml
├── .env.example
├── requirements.txt
│
├── .claude/                           # Claude Code 인프라
│   ├── settings.json                  # 훅 설정
│   ├── skills/
│   │   ├── skill-rules.json           # 자동 활성화 규칙
│   │   ├── scrapling-guidelines/      # 크롤링 가이드라인
│   │   ├── playwright-guidelines/     # 발행 자동화 가이드라인
│   │   ├── naver-seo/                 # SEO 최적화 규칙
│   │   └── medical-ad-law/            # 의료광고법 (enforcement: block)
│   ├── agents/
│   ├── commands/
│   └── hooks/
│
├── dev/active/                        # 외부 기억 장치
│
├── src/
│   ├── config.py                      # 환경설정
│   ├── analyzer/                      # 패턴 분석 (Scrapling)
│   │   ├── serp_collector.py          # 상위 URL 수집
│   │   ├── content_parser.py          # 본문 구조 추출
│   │   └── pattern_extractor.py       # 통합 패턴 생성
│   ├── generator/                     # 콘텐츠 생성
│   │   ├── prompt_builder.py          # 프롬프트 조립
│   │   ├── content_generator.py       # Claude API 호출
│   │   └── image_generator.py         # Nano Banana Pro + EXIF
│   ├── publisher/                     # 자동 발행 (Playwright)
│   │   ├── auth.py                    # 로그인 처리
│   │   ├── editor.py                  # 에디터 조작
│   │   ├── stealth.py                 # 봇 탐지 우회
│   │   └── scheduler.py               # 발행 스케줄링
│   ├── utils/
│   │   ├── exif.py                    # EXIF 메타데이터 삽입
│   │   ├── medical_ad_checker.py      # 의료광고법 검증
│   │   └── naver_api.py               # 네이버 API 래퍼
│   └── cli.py                         # CLI 인터페이스
│
├── prompts/
│   ├── system_prompt.md               # 시스템 프롬프트
│   └── pattern_injection.md           # 패턴 주입 템플릿
│
├── n8n/workflows/
│   ├── main_pipeline.json             # 메인 파이프라인
│   ├── publish_scheduler.json         # 발행 스케줄러
│   └── error_recovery.json            # 에러 복구
│
└── tests/
    ├── test_analyzer.py
    ├── test_generator.py
    ├── test_publisher.py
    └── test_stealth.py
```

---

## 4. 빌드/실행 명령어

### 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

### CLI 실행
```bash
# 키워드 분석
python -m src.cli analyze --keyword "키워드"

# 원고 생성
python -m src.cli generate --keyword-id <uuid>

# 발행
python -m src.cli publish --draft-id <uuid>

# 스케줄 확인
python -m src.cli check-schedule
```

### Docker 실행
```bash
docker-compose up -d
```

### 테스트
```bash
pytest tests/ -v
```

---

## 5. 아키텍처 패턴

### 5.1 라이브러리 역할 분리 (중요)

```
Scrapling (StealthyFetcher)     → 읽기 전용 (크롤링, 데이터 수집)
Playwright (raw)                → 쓰기 작업 (에디터 조작, 발행)
```

**두 라이브러리의 역할을 절대 혼용하지 말 것.**

### 5.2 이미지 생성 (Nano Banana Pro)

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

# 이미지 추출
for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image_bytes = part.inline_data.data
        # → JPEG 저장 → exif.inject_exif() → 최종 파일
```

### 5.3 발행 모드

```python
PUBLISH_MODES = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal":       {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive":   {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}
```

- **하루 5개 초과 금지**
- 의료 키워드는 conservative 권장
- 발행 시간대: 09:00 ~ 18:00
- 타이핑 딜레이: 50~200ms
- 오타 확률: 2%

### 5.4 의료광고법 검증 프로세스

```
원고 생성 → medical_ad_checker.check_violations(text)
→ critical 있음? → Claude에 수정 재요청 (max 2회) → 여전히 위반 → 수동 검수 + Slack 알림
→ warning만? → 로깅 + 주석 추가 → 정상 진행
→ 위반 없음 → 정상 진행
```

---

## 6. 주의사항

### 6.1 의료광고법 준수 (enforcement: block)

| # | 카테고리 | severity |
|---|----------|----------|
| 1 | 치료효과 오인 유발 | critical |
| 2 | 거짓/과장 표현 | critical |
| 3 | 비교/비방 | critical |
| 4 | 부작용 정보 누락 | warning |
| 5 | 법적 근거 없는 자격 | critical |
| 6 | 기사/전문가 위장 | warning |
| 7 | 인증/보증 부당 사용 | warning |
| 8 | 소비자 유인 (할인) | warning |

**critical 위반 시 작업 중단. 수동 검수 필수.**

### 6.2 봇 탐지 우회

- user_data_dir 세션 유지
- 클립보드 우회 로그인 (Pyperclip)
- human_typing: 단락별 타이핑, 랜덤 딜레이
- EXIF 메타데이터 삽입 (카메라 정보, 날짜)
- 발행 간격 준수 (min 2시간 이상)

### 6.3 API 에러 처리

- **Nano Banana Pro 429**: exponential backoff (10s, 30s, 60s)
- **Safety filter**: 프롬프트 수정 후 재시도 (max 3회)
- **발행 실패**: 자동 재스케줄 (max 3회)

### 6.4 코딩 컨벤션

- Python 3.11+ 타입 힌트 필수
- async/await 패턴 사용
- JSON 구조화 출력 (Claude API)
- 종료코드: 0=성공, 1=실패

---

## 7. 환경변수

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
```

---

## 8. DB 테이블

| 테이블 | 용도 |
|--------|------|
| keywords | 키워드 관리 (status: pending/analyzing/done) |
| patterns | 상위노출 패턴 데이터 |
| drafts | 생성된 원고 (status: draft/published/failed) |
| publish_logs | 발행 이력 로깅 |

---

## 9. n8n 워크플로우

| 워크플로우 | 스케줄 | 기능 |
|------------|--------|------|
| Main Pipeline | 매일 09:00 | 키워드 조회 → 패턴 분석 → 원고 생성 |
| Publish Scheduler | 10분 간격 | 발행 예정 드래프트 확인 → 조건 충족 시 발행 |
| Daily Report | 매일 21:00 | 당일 발행 결과 집계 → Slack 리포트 |

---

## 10. Skills / Agents / Hooks

### Skills (enforcement)
| Skill | Enforcement | 설명 |
|-------|-------------|------|
| scrapling-guidelines | suggest | 크롤링 가이드라인 |
| playwright-guidelines | suggest | 발행 자동화 가이드라인 |
| naver-seo | suggest | SEO 최적화 규칙 |
| medical-ad-law | **block** | 위반 시 작업 중단 |

### Agents
- planner, plan-reviewer: 계획 수립/검토
- code-architecture-reviewer: 코드 아키텍처 검토
- auto-error-resolver: 자동 에러 해결
- pipeline-runner: 파이프라인 반복 실행
- debug-publisher: 발행 디버깅

### Hooks
- skill-activation-prompt.sh (UserPromptSubmit)
- post-tool-use-tracker.sh (PostToolUse)
- build-check.sh (Stop)

---

## 11. 인프라 파일 동기화 체크리스트

- [ ] SPEC.md 변경 → CLAUDE.md 업데이트
- [ ] requirements.txt 의존성 최신화
- [ ] .env.example 환경변수 동기화
- [ ] docker-compose.yml 서비스 정의
- [ ] .claude/skills/ 스킬 파일 정합성
- [ ] n8n/workflows/ 워크플로우 JSON 검증

---

## 12. 개발 로드맵

| Phase | 작업 | 검증 기준 |
|-------|------|-----------|
| 1 | 인프라 + analyzer 모듈 | `cli analyze` 성공 |
| 2 | generator 모듈 + 의료광고법 검증 | `cli generate` 성공 |
| 3 | publisher + n8n 통합 | `cli publish` + e2e 성공 |

---

*Last updated: 2025-03*
