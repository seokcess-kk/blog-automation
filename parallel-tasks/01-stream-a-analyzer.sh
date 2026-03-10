#!/bin/bash
# ============================================================
# 01-stream-a-analyzer.sh — Stream A: 상위노출 패턴 분석 모듈
# ============================================================
# 실행: ./parallel-tasks/01-stream-a-analyzer.sh
# 조건: Phase 0 완료 후
# 담당: src/analyzer/* (이 폴더만 수정)
# 금지: src/generator/*, src/publisher/*, src/utils/* 수정 금지
# 소요: 1~2시간
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Stream A: analyzer 모듈 개발"
echo "  담당 파일: src/analyzer/*"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

claude -p "
SPEC.md 섹션 4.1 (analyzer)을 읽고 상위노출 패턴 분석 모듈을 구현해줘.

## 범위 (이 파일들만 수정)
- src/analyzer/__init__.py
- src/analyzer/serp_collector.py
- src/analyzer/content_parser.py
- src/analyzer/pattern_extractor.py

## ⚠️ 절대 수정 금지
- src/generator/*, src/publisher/*, src/utils/*
- config.py (import만 허용, 수정 금지)

## 구현 순서

### 1. serp_collector.py
- 네이버 검색 API로 키워드 검색 → 상위 5개 블로그 URL 반환
- 네이버 API 호출: src/utils/naver_api.py를 import (아직 없으면 인터페이스만 맞춰서 stub)
- 폴백: Scrapling StealthyFetcher로 직접 검색
- 입력: keyword (str)
- 출력: List[str] (URL 목록)
- 에러: 빈 결과 → [], 차단 → 3회 재시도

### 2. content_parser.py
- Scrapling StealthyFetcher로 블로그 페이지 로드
- headless=True, network_idle=True
- auto_save=True (Adaptive 셀렉터 대비)
- .se-main-container CSS 셀렉터로 본문 추출
- SE 에디터 / 구 에디터 DOM 구조 차이 처리
- 출력 dict: url, title, char_count, image_count, heading_count, headings, keyword_in_title, keyword_positions, image_positions, has_list, has_table, related_keywords

### 3. pattern_extractor.py
- content_parser 결과 5개 → 통합 패턴 JSON
- 평균/빈도 계산, 제목 패턴 추출, 연관 키워드 교집합
- 출력 dict: avg_char_count, avg_image_count, avg_heading_count, title_patterns, keyword_placement, related_keywords, content_structure, image_position_pattern

### 4. __init__.py
- analyze_keyword(keyword: str) -> dict 함수 export
- serp_collector → content_parser → pattern_extractor 파이프라인 조합

## 코딩 규칙
- Python 3.11+, 타입 힌트 필수
- 모든 함수에 docstring
- logging 모듈 사용 (print 금지)
- try/except + 로깅
- from src.config import ... 로 설정 로드

## 검증
완료 후 다음 명령이 에러 없이 실행되는지 확인:
python -c 'from src.analyzer import analyze_keyword; print(\"import OK\")'
"
