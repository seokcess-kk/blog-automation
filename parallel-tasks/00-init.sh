#!/bin/bash
# ============================================================
# 00-init.sh — Phase 0: 인프라 초기화 (단독 실행)
# ============================================================
# 실행: ./parallel-tasks/00-init.sh
# 조건: SPEC.md + 법령 파일이 프로젝트 루트에 있어야 함
# 소요: 30~60분
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 0: blog-automation 인프라 초기화"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 사전 조건 확인
if [ ! -f "$PROJECT_DIR/SPEC.md" ]; then
    echo "❌ SPEC.md가 프로젝트 루트에 없습니다."
    echo "   SPEC.md를 먼저 배치해주세요."
    exit 1
fi

echo "✅ SPEC.md 확인 완료"
echo ""
echo "Claude Code에 다음 작업을 지시합니다..."
echo ""

# Claude Code 실행
claude -p "
SPEC.md를 읽고 blog-automation 프로젝트 인프라를 초기화해줘.

## 작업 순서 (반드시 이 순서대로)

### 1단계: 디렉토리 구조 생성
SPEC.md 섹션 2의 디렉토리 구조를 그대로 생성해.
모든 __init__.py 파일 포함.

### 2단계: requirements.txt 생성
\`\`\`
# Core
python-dotenv>=1.0
click>=8.0

# Scraping/Analysis
scrapling[stealth]>=0.3

# Browser Automation
playwright>=1.40
pyperclip>=1.8

# AI APIs
anthropic>=0.40
google-genai>=1.0

# Image Processing
Pillow>=10.0
piexif>=1.1

# Database
supabase>=2.0

# Testing
pytest>=8.0
pytest-asyncio>=0.23
\`\`\`

### 3단계: .env.example 생성
SPEC.md 섹션 9의 환경변수 목록 그대로.

### 4단계: config.py 생성
SPEC.md 섹션 6의 PUBLISH_MODES 설정 + 환경변수 로딩.
python-dotenv 사용. 모든 상수에 타입 힌트.

### 5단계: CLAUDE.md 생성
SPEC.md 섹션 11의 가이드를 따라 작성.
분량 5~15KB. 실행 명령어는 복붙 가능하게.

### 6단계: Skills 생성 (4개)
SPEC.md 섹션 12 참조.
- .claude/skills/scrapling-guidelines/SKILL.md
- .claude/skills/playwright-guidelines/SKILL.md
- .claude/skills/naver-seo/SKILL.md
- .claude/skills/medical-ad-law/SKILL.md (enforcement: block)
  → resources/ 폴더의 법령 원문 파일 (law-article-56.md, law-article-57.md, enforcement-23.md) 참조하여 작성

### 7단계: skill-rules.json 생성
바이브코딩 v2.0 형식. 4개 스킬의 자동 활성화 규칙.
medical-ad-law는 enforcement: block.

### 8단계: Agents 생성 (6개)
SPEC.md 섹션 12.2 참조.
planner, plan-reviewer, code-architecture-reviewer,
auto-error-resolver, pipeline-runner, debug-publisher

### 9단계: Hooks 생성 (3개)
SPEC.md 섹션 12.3 참조.
skill-activation-prompt.sh, post-tool-use-tracker.sh, build-check.sh
+ .claude/settings.json 등록

### 10단계: DB 스키마 SQL 파일 생성
SPEC.md 섹션 3의 4개 테이블을 supabase/schema.sql로 저장.

## 검증
완료 후 디렉토리 트리 출력하여 SPEC.md와 일치하는지 확인.
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 0 완료 확인 후 Phase 1 진행하세요"
echo "  → 터미널 4개로 01~04 스크립트 동시 실행"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
