# blog-automation SPEC.md

> 네이버 블로그 자동화 파이프라인
> 키워드 분석 → 상위노출 패턴 역분석 → 원고 생성 → 자동 발행
> SDD(Spec Driven Development) + DDD(Domain Driven Design) 기반

---

## 1. 프로젝트 개요

### 1.1 한 줄 소개
네이버 블로그 상위노출 패턴을 역분석하여 SEO 최적화된 콘텐츠를 자동 생성하고, 봇 탐지를 우회하여 자동 발행하는 end-to-end 파이프라인.

### 1.2 핵심 파이프라인
```
키워드 입력 → 상위노출 패턴 분석(Scrapling) → 원고 생성(Claude API) → 이미지 생성(Nano Banana Pro) + EXIF 삽입 → 자동 발행(Playwright) → 결과 로깅
```

### 1.3 성공 기준
- [ ] 키워드 입력 → 원고+이미지 생성까지 자동화 (5분 이내)
- [ ] 블로그 자동 발행 성공률 90% 이상
- [ ] 의료광고법 위반 표현 0건 (자동 검증)
- [ ] 무인 운영 1주일 성공 (Phase 2 마일스톤)

### 1.4 기술 스택
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

### 1.5 Scrapling vs Playwright 역할 분담

⚠️ **두 라이브러리의 역할을 절대 혼용하지 말 것.**

```
Scrapling (StealthyFetcher)     → 읽기 전용 (크롤링, 데이터 수집)
Playwright (raw)                → 쓰기 작업 (에디터 조작, 발행)
```

### 1.6 Nano Banana Pro 상세
```
모델: gemini-3-pro-image-preview
호출: Google AI Studio API (google-genai SDK)
워터마크: AI Studio 경로 → SynthID 육안 워터마크 없음
응답: response.candidates[0].content.parts → image part → base64 디코딩
```

---

## 2. 디렉토리 구조 (바이브코딩 v2.0 기반)

```
blog-automation/
├── CLAUDE.md                          # Phase 1: 프로젝트 기억
├── SPEC.md                            # Phase 0: 주문서
├── docker-compose.yml
├── .env.example
├── requirements.txt
│
├── .claude/                           # Claude Code 인프라
│   ├── settings.json                  # Phase 5: 훅 설정
│   ├── skills/
│   │   ├── skill-rules.json           # Phase 3: 자동 활성화
│   │   ├── scrapling-guidelines/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   ├── playwright-guidelines/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       └── naver-editor.md
│   │   ├── naver-seo/
│   │   │   └── SKILL.md
│   │   └── medical-ad-law/
│   │       ├── SKILL.md               # enforcement: block
│   │       └── resources/
│   │           ├── law-article-56.md
│   │           ├── law-article-57.md
│   │           └── enforcement-23.md
│   ├── agents/
│   │   ├── planner.md
│   │   ├── plan-reviewer.md
│   │   ├── code-architecture-reviewer.md
│   │   ├── auto-error-resolver.md
│   │   ├── pipeline-runner.md
│   │   └── debug-publisher.md
│   ├── commands/
│   │   └── dev-docs.md
│   └── hooks/
│       ├── skill-activation-prompt.sh
│       ├── post-tool-use-tracker.sh
│       └── build-check.sh
│
├── dev/active/                        # Phase 4-B: 외부 기억 장치
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── serp_collector.py
│   │   ├── content_parser.py
│   │   └── pattern_extractor.py
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py
│   │   ├── content_generator.py
│   │   └── image_generator.py         # Nano Banana Pro + EXIF
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── editor.py
│   │   ├── stealth.py
│   │   └── scheduler.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── exif.py
│   │   ├── medical_ad_checker.py
│   │   └── naver_api.py
│   └── cli.py
│
├── prompts/
│   ├── system_prompt.md
│   └── pattern_injection.md
│
├── n8n/workflows/
│   ├── main_pipeline.json
│   ├── publish_scheduler.json
│   └── error_recovery.json
│
└── tests/
    ├── test_analyzer.py
    ├── test_generator.py
    ├── test_publisher.py
    └── test_stealth.py
```

---

## 3. DB 스키마 (Supabase)

### keywords
```sql
CREATE TABLE keywords (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword TEXT NOT NULL, blog_id TEXT NOT NULL,
  target_region TEXT, content_angle TEXT,
  status TEXT DEFAULT 'pending',
  schedule_date DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### patterns
```sql
CREATE TABLE patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
  source_urls TEXT[], avg_char_count INT, avg_image_count INT,
  avg_heading_count INT, title_patterns JSONB,
  keyword_placement JSONB, related_keywords TEXT[],
  content_structure JSONB, raw_data JSONB,
  analyzed_at TIMESTAMPTZ DEFAULT now()
);
```

### drafts
```sql
CREATE TABLE drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
  pattern_id UUID REFERENCES patterns(id),
  title TEXT NOT NULL, body_html TEXT NOT NULL,
  tags TEXT[], meta_description TEXT, images JSONB,
  status TEXT DEFAULT 'draft',
  publish_at TIMESTAMPTZ, published_at TIMESTAMPTZ,
  naver_post_url TEXT, error_log TEXT,
  retry_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### publish_logs
```sql
CREATE TABLE publish_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id UUID REFERENCES drafts(id) ON DELETE CASCADE,
  blog_id TEXT NOT NULL, action TEXT NOT NULL,
  status TEXT NOT NULL, error_detail TEXT,
  duration_seconds FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. 모듈별 상세 스펙

### 4.1 analyzer (Scrapling 전용)
- **serp_collector.py**: 네이버 검색 API → 상위 5개 URL 수집. 폴백: Scrapling StealthyFetcher
- **content_parser.py**: URL → 본문 구조 추출 (글자수, 이미지수, 소제목, 키워드 배치)
- **pattern_extractor.py**: 5개 결과 → 통합 패턴 JSON

### 4.2 generator
- **prompt_builder.py**: System + Pattern Injection + User 3계층 프롬프트 조립
- **content_generator.py**: Claude API (claude-sonnet-4-20250514), temperature 0.7, JSON 출력
- **image_generator.py**: Nano Banana Pro API 호출 → base64 이미지 추출 → EXIF 삽입

#### image_generator.py 상세
```python
# 호출 패턴
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

# 에러 처리
# 429 → exponential backoff (10s, 30s, 60s)
# safety filter → 프롬프트 수정 후 재시도 (max 3회)
```

### 4.3 publisher (Playwright 전용)
- **auth.py**: Pyperclip 클립보드 우회 로그인, user_data_dir 세션 유지
- **editor.py**: iframe 진입 → 단락별 human_typing → 이미지 업로드 → 발행
- **stealth.py**: human_delay, human_typing (50~200ms, 2% 오타), 핑거프린트 랜덤화
- **scheduler.py**: 3단계 발행 모드 (conservative/normal/aggressive)

### 4.4 utils
- **exif.py**: 카메라 EXIF 삽입 (iPhone/Galaxy 랜덤, 1~7일 내 날짜)
- **medical_ad_checker.py**: 의료광고법 위반 검증 (섹션 7 참조)
- **naver_api.py**: 네이버 검색 API 래퍼

### 4.5 cli.py
```bash
python -m src.cli analyze --keyword "키워드"
python -m src.cli generate --keyword-id <uuid>
python -m src.cli publish --draft-id <uuid>
python -m src.cli check-schedule
# 출력: JSON, 종료코드: 0=성공 1=실패
```

---

## 5. n8n 워크플로우 설계

### Workflow 1: Main Pipeline (매일 09:00)
키워드 조회 → 패턴 분석 → 원고 생성 → 결과 알림

### Workflow 2: Publish Scheduler (10분 간격)
발행 예정 드래프트 확인 → 조건 충족 시 발행 → 실패 시 재스케줄 (max 3회)

### Workflow 3: Daily Report (매일 21:00)
당일 발행 결과 집계 → Slack 리포트

---

## 6. 봇 탐지 우회 스펙

### 발행 모드 (config.py)
```python
PUBLISH_MODES = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal":       {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive":   {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "conservative")
PUBLISH_HOUR_RANGE = (9, 18)
TYPING_DELAY_MS = (50, 200)
TYPO_PROBABILITY = 0.02
MAX_RETRY_COUNT = 3
```
⚠️ 5개 초과 금지. 의료 키워드는 conservative 권장.

---

## 7. 의료광고법 준수 스펙

### 7.1 적용 법령
- 의료법 제56조 (의료광고의 금지 등)
- 의료법 제57조 (의료광고의 심의)
- 시행령 제23조 (의료광고의 금지 기준)
- 벌칙: 제89조 (1년 이하 징역 / 1천만원 이하 벌금)
- 행정처분: 제63조 (시정명령), 제64조 (허가취소), 제67조 (과징금 5천만원 이하)
- 원문 보관: .claude/skills/medical-ad-law/resources/

### 7.2 자동 검증 카테고리 (medical_ad_checker.py)

| # | 카테고리 | 법령 근거 | severity |
|---|----------|-----------|----------|
| 1 | 치료효과 오인 유발 | 법56조②2호, 시행령23조①2호 | critical |
| 2 | 거짓/과장 표현 | 법56조②3,8호, 시행령23조①3,8호 | critical |
| 3 | 비교/비방 | 법56조②4,5호, 시행령23조①4,5호 | critical |
| 4 | 부작용 정보 누락 | 법56조②7호, 시행령23조①7호 | warning |
| 5 | 법적 근거 없는 자격 | 법56조②9호 | critical |
| 6 | 기사/전문가 위장 | 법56조②10호, 시행령23조①10호 | warning |
| 7 | 인증/보증 부당 사용 | 법56조②14호 | warning |
| 8 | 소비자 유인 (할인) | 법56조②13호, 시행령23조①13호 | warning |

### 7.3 검증 프로세스
```
원고 생성 → medical_ad_checker.check_violations(text)
→ critical 있음? → Claude에 수정 재요청 (max 2회) → 여전히 위반 → 수동 검수 + Slack 알림
→ warning만? → 로깅 + 주석 추가 → 정상 진행
→ 위반 없음 → 정상 진행
```

---

## 8. 프롬프트 템플릿

### System Prompt 핵심 구조 (prompts/system_prompt.md)
```
역할 정의 → 의료광고법 9대 금지 사항 → 권장 표현 → JSON 출력 포맷
```
금지 사항은 섹션 7의 법령 근거를 직접 반영.

### Pattern Injection (prompts/pattern_injection.md)
```
{{keyword}}, {{region}} + 상위 5개 패턴 데이터 → 작성 지침 7개 항목
```

---

## 9. 환경변수 (.env)
```bash
SUPABASE_URL=     SUPABASE_KEY=
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=              # Nano Banana Pro
NAVER_CLIENT_ID=  NAVER_CLIENT_SECRET=
BLOG_A_USERNAME=  BLOG_A_PASSWORD=
BLOG_B_USERNAME=  BLOG_B_PASSWORD=
SLACK_WEBHOOK_URL=
PUBLISH_MODE=conservative       # conservative|normal|aggressive
```

---

## 10. 개발 순서

| Phase | 기간 | 작업 | 검증 |
|-------|------|------|------|
| 1 | Week 1-2 | 인프라 + analyzer 모듈 | `cli analyze` 성공 |
| 2 | Week 3-4 | generator 모듈 + 의료광고법 검증 | `cli generate` 성공 |
| 3 | Week 5-6 | publisher + n8n 통합 | `cli publish` + e2e 성공 |

---

## 11. CLAUDE.md 구성 가이드

필수 섹션: 프로젝트 구조, 기술 스택 (버전), 빌드/실행 명령어, 아키텍처 패턴, 주의사항, 인프라 파일 동기화 체크리스트.
분량: 5~15KB.

---

## 12. Skills / Agents / Hooks

### Skills (enforcement 포함)
- scrapling-guidelines (suggest)
- playwright-guidelines (suggest)
- naver-seo (suggest)
- medical-ad-law (**block** — 위반 시 작업 중단)

### Agents
- planner, plan-reviewer, code-architecture-reviewer, auto-error-resolver
- pipeline-runner (반복), debug-publisher (반복)

### Hooks
- skill-activation-prompt.sh (UserPromptSubmit)
- post-tool-use-tracker.sh (PostToolUse)
- build-check.sh (Stop — 수동 테스트 후 등록)
