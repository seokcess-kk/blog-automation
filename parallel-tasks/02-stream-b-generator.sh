#!/bin/bash
# ============================================================
# 02-stream-b-generator.sh — Stream B: 콘텐츠 생성 모듈
# ============================================================
# 실행: ./parallel-tasks/02-stream-b-generator.sh
# 조건: Phase 0 완료 후
# 담당: src/generator/*, prompts/*
# 금지: src/analyzer/*, src/publisher/*, src/utils/* 수정 금지
# 소요: 1~2시간
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Stream B: generator 모듈 개발"
echo "  담당 파일: src/generator/*, prompts/*"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

claude -p "
SPEC.md 섹션 4.2 (generator) + 섹션 8 (프롬프트 템플릿)을 읽고 콘텐츠 생성 모듈을 구현해줘.

## 범위 (이 파일들만 수정)
- src/generator/__init__.py
- src/generator/prompt_builder.py
- src/generator/content_generator.py
- src/generator/image_generator.py
- prompts/system_prompt.md
- prompts/pattern_injection.md

## ⚠️ 절대 수정 금지
- src/analyzer/*, src/publisher/*, src/utils/*
- config.py (import만 허용)

## 구현 순서

### 1. prompts/system_prompt.md
SPEC.md 섹션 8.1 그대로 작성.
의료광고법 9대 금지 사항 포함 (SPEC.md 섹션 7 참조).
JSON 출력 포맷 명시.

### 2. prompts/pattern_injection.md
SPEC.md 섹션 8.2 그대로 작성.
{{변수}} 플레이스홀더 포함.

### 3. prompt_builder.py
- prompts/ 디렉토리에서 md 파일 로드
- {{keyword}}, {{region}}, {{avg_char_count}} 등 변수 치환
- 입력: keyword, region, content_angle, pattern_data (dict)
- 출력: dict { system: str, user: str }

### 4. content_generator.py
- Anthropic Python SDK 사용
- model: claude-sonnet-4-20250514
- max_tokens: 4096, temperature: 0.7
- JSON 응답 파싱 (실패 시 regex 추출 → 재요청 max 2회)
- rate limit: exponential backoff
- 의료광고법 검증: src/utils/medical_ad_checker.py를 import (stub 가능)
  → critical 위반 시 수정 프롬프트로 재생성

### 5. image_generator.py ⭐ (Nano Banana Pro)
- google-genai SDK 사용
- model: gemini-3-pro-image-preview

호출 패턴:
\`\`\`python
from google import genai

client = genai.Client(api_key=config.GOOGLE_AI_API_KEY)
response = client.models.generate_content(
    model='gemini-3-pro-image-preview',
    contents=prompt_text,
    config=genai.types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
    ),
)

for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image_bytes = part.inline_data.data
        # → JPEG 저장 → exif.inject_exif() 호출
\`\`\`

- 프롬프트 가공: 원본 + ', professional blog illustration, clean design, Korean aesthetic, no text'
- EXIF 삽입: src/utils/exif.py import (stub 가능)
- 에러: 429 → backoff (10s, 30s, 60s), safety filter → 프롬프트 수정 재시도 (max 3)

### 6. __init__.py
- generate_content(keyword_id: str) -> dict 함수 export
- prompt_builder → content_generator → image_generator 파이프라인

## 코딩 규칙
- Python 3.11+, 타입 힌트 필수
- 모든 함수에 docstring
- logging 모듈 사용
- 환경변수는 config.py에서 로드

## 검증
python -c 'from src.generator import generate_content; print(\"import OK\")'
"
