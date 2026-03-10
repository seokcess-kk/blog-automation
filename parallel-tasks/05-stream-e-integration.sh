#!/bin/bash
# ============================================================
# 05-stream-e-integration.sh — Stream E: CLI + n8n + 테스트 통합
# ============================================================
# 실행: ./parallel-tasks/05-stream-e-integration.sh
# 조건: Phase 1 (Stream A~D) 모두 완료 후
# 담당: src/cli.py, n8n/*, tests/*, docker-compose.yml
# 금지: 모듈 내부 로직 수정 금지 (인터페이스만 연결)
# 소요: 1~2시간
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Stream E: CLI + n8n 통합 + 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 사전 조건: 모든 모듈 import 가능 확인
echo "모듈 import 사전 검증..."
python3 -c "
from src.analyzer import analyze_keyword
from src.generator import generate_content
from src.publisher import publish_draft
from src.utils.medical_ad_checker import check_violations
from src.utils.exif import inject_exif
from src.utils.naver_api import search_blog
print('✅ 모든 모듈 import 성공')
" || {
    echo "❌ 모듈 import 실패. Stream A~D가 완료되었는지 확인하세요."
    exit 1
}

claude -p "
SPEC.md 섹션 4.5 (cli) + 섹션 5 (n8n 워크플로우)를 읽고 통합 작업을 해줘.

## 범위 (이 파일들만 생성/수정)
- src/cli.py
- n8n/workflows/main_pipeline.json
- n8n/workflows/publish_scheduler.json
- n8n/workflows/error_recovery.json
- docker-compose.yml
- tests/test_analyzer.py
- tests/test_generator.py
- tests/test_publisher.py
- tests/test_stealth.py

## ⚠️ 금지
- src/analyzer/*, src/generator/*, src/publisher/*, src/utils/* 내부 수정 금지
- 이미 구현된 모듈의 인터페이스를 변경하지 말 것

## 구현 순서

### 1. src/cli.py (click 프레임워크)
\`\`\`python
import click

@click.group()
def cli():
    pass

@cli.command()
@click.option('--keyword', required=True)
def analyze(keyword: str):
    '''키워드 → 패턴 분석 → DB 저장'''
    # src.analyzer.analyze_keyword() 호출
    # 결과를 Supabase patterns 테이블에 저장
    # JSON 출력 (n8n 파싱용)

@cli.command()
@click.option('--keyword-id', required=True)
def generate(keyword_id: str):
    '''키워드ID → 패턴 로드 → 원고 생성 → DB 저장'''
    # Supabase에서 pattern 로드
    # src.generator.generate_content() 호출
    # 결과를 drafts 테이블에 저장
    # publish_at 시간 생성 (scheduler.generate_publish_time)
    # JSON 출력

@cli.command()
@click.option('--draft-id', required=True)
def publish(draft_id: str):
    '''드래프트ID → 로그인 → 발행'''
    # Supabase에서 draft 로드
    # scheduler.check_daily_limit + get_min_interval_ok 확인
    # src.publisher.publish_draft() 호출
    # 결과를 publish_logs에 기록
    # drafts.status 업데이트
    # JSON 출력

@cli.command()
def check_schedule():
    '''발행 예정 드래프트 확인 → 조건 충족 시 publish'''
    # drafts에서 publish_at <= now() AND status='ready' 조회
    # 있으면 publish 호출
    # JSON 출력 (발행한 draft_id 또는 빈 리스트)
\`\`\`

출력 형식: 모든 명령어가 JSON stdout으로 결과 반환
종료 코드: 0=성공, 1=실패
에러 시: {\"success\": false, \"error\": \"메시지\"} 출력

### 2. docker-compose.yml
\`\`\`yaml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - '5678:5678'
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=\${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=\${N8N_PASSWORD}
    volumes:
      - n8n_data:/home/node/.n8n
      - ./:/app  # 프로젝트 마운트 (Execute Command용)
    working_dir: /app
    restart: unless-stopped

volumes:
  n8n_data:
\`\`\`

### 3. n8n 워크플로우 JSON (3개)
SPEC.md 섹션 5 구조를 n8n JSON export 형식으로 작성.
각 워크플로우에 Execute Command 노드가 cli.py를 호출하는 구조.

### 4. 테스트 파일 (4개)
pytest 기반. 실제 API 호출 테스트는 @pytest.mark.live로 분리.

test_analyzer.py:
- test_serp_collector_returns_list
- test_content_parser_output_schema
- test_pattern_extractor_averages

test_generator.py:
- test_prompt_builder_variable_substitution
- test_content_generator_json_parsing (mock)
- test_image_generator_exif_applied (mock)

test_publisher.py:
- test_scheduler_daily_limit
- test_scheduler_min_interval
- test_scheduler_publish_time_range

test_stealth.py:
- test_human_delay_range
- test_human_typing_includes_typos
- test_typing_delay_range

## 검증
\`\`\`bash
# 모든 테스트 통과
pytest tests/ -v --ignore=tests/*live*

# CLI 도움말 출력
python -m src.cli --help
python -m src.cli analyze --help
python -m src.cli generate --help
python -m src.cli publish --help

# Docker Compose 문법 검증
docker compose config
\`\`\`
"
