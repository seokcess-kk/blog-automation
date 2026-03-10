#!/bin/bash
# ============================================================
# 04-stream-d-utils.sh — Stream D: 유틸리티 모듈
# ============================================================
# 실행: ./parallel-tasks/04-stream-d-utils.sh
# 조건: Phase 0 완료 후
# 담당: src/utils/*
# 금지: src/analyzer/*, src/generator/*, src/publisher/* 수정 금지
# 소요: 1~1.5시간
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Stream D: utils 모듈 개발"
echo "  담당 파일: src/utils/*"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

claude -p "
SPEC.md 섹션 4.4 (utils) + 섹션 7 (의료광고법)을 읽고 유틸리티 모듈을 구현해줘.

## 범위 (이 파일들만 수정)
- src/utils/__init__.py
- src/utils/exif.py
- src/utils/medical_ad_checker.py
- src/utils/naver_api.py

## ⚠️ 절대 수정 금지
- src/analyzer/*, src/generator/*, src/publisher/*
- config.py (import만 허용)

## 구현 순서

### 1. naver_api.py
\`\`\`python
def search_blog(keyword: str, display: int = 5) -> list[dict]:
    '''네이버 검색 API (blog 검색) 호출.
    반환: [{title, link, description, bloggername, postdate}]
    환경변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (config에서 로드)
    에러: requests.HTTPError → 로깅 후 빈 리스트'''
\`\`\`
- requests 라이브러리 사용
- 헤더: X-Naver-Client-Id, X-Naver-Client-Secret
- URL: https://openapi.naver.com/v1/search/blog.json

### 2. exif.py
\`\`\`python
CAMERAS = [
    ('Apple', 'iPhone 14 Pro'),
    ('Apple', 'iPhone 15'),
    ('Samsung', 'SM-S918N'),     # Galaxy S23 Ultra
    ('Samsung', 'SM-A546N'),     # Galaxy A54
    ('Samsung', 'SM-S926N'),     # Galaxy S24+
]

def inject_exif(
    image_path: str,
    output_path: str,
    region_gps: tuple[float, float] | None = None
) -> str:
    '''AI 이미지에 카메라 EXIF 삽입.
    - Make, Model: CAMERAS에서 랜덤
    - DateTime: 최근 1~7일 내 랜덤
    - FocalLength: 24~70mm 랜덤
    - GPS: region_gps 제공 시 ± 미세 오프셋
    - 반환: output_path
    - ⚠️ 입력이 PNG면 JPEG로 변환 (EXIF는 JPEG만 지원)'''
\`\`\`
- Pillow + piexif 사용

### 3. medical_ad_checker.py ⭐ (가장 중요)

⚠️ 이 모듈은 의료법 제56조 + 시행령 제23조에 직접 근거한다.
⚠️ .claude/skills/medical-ad-law/resources/ 의 법령 원문 파일을 반드시 참조하라.
⚠️ 금칙어를 임의로 축소하거나 변경하지 말 것.

\`\`\`python
@dataclass
class Violation:
    word: str              # 위반 단어/패턴
    position: int          # 텍스트 내 위치
    category: str          # 카테고리명
    severity: str          # 'critical' | 'warning'
    law_reference: str     # 법령 근거 (예: '법56조②2호, 시행령23조①2호')
    suggestion: str        # 대체 표현 제안

def check_violations(text: str) -> list[Violation]:
    '''의료광고법 위반 표현 검증'''

def has_critical(violations: list[Violation]) -> bool:
    '''critical 위반 존재 여부'''

def get_violation_summary(violations: list[Violation]) -> str:
    '''위반 요약 텍스트 (Slack 알림용)'''
\`\`\`

금칙어 카테고리 (SPEC.md 섹션 7.2 + enforcement-23.md 참조):

**카테고리 1: 치료효과 오인 (critical)**
법근거: 법56조②2호, 시행령23조①2호
금칙어: 확실, 보장, 완치, 100%, 반드시 효과, 틀림없이
       후기, 체험기, 경험담, 직접 해본, 실제 효과, 치료 후기

**카테고리 2: 거짓/과장 (critical)**
법근거: 법56조②3,8호, 시행령23조①3,8호
금칙어: 최고, 최초, 유일, 독보적, 압도적, 최상의, 국내 유일
       획기적, 혁신적, 기적의, 놀라운 효과, 완벽한
       부작용 없는, 통증 없는, 100% 안전, 무조건

**카테고리 3: 비교/비방 (critical)**
법근거: 법56조②4,5호, 시행령23조①4,5호
금칙어: ~보다 우수, ~보다 효과적, ~보다 안전, (타 병원명)

**카테고리 4: 부작용 누락 (warning)**
법근거: 법56조②7호, 시행령23조①7호
검증: 시술/한약 언급 시 부작용/개인차 미언급 → warning

**카테고리 5: 무자격 명칭 (critical)**
법근거: 법56조②9호
금칙어: 명의, 대한민국 대표, (비공식 자격)

**카테고리 6: 기사 위장 (warning)**
법근거: 법56조②10호, 시행령23조①10호
검증: 기사 형태 + 연락처/주소 동시 노출

**카테고리 7: 인증 부당 사용 (warning)**
법근거: 법56조②14호
검증: 법정 예외 외 인증/보증/추천 표시

**카테고리 8: 소비자 유인 (warning)**
법근거: 법56조②13호, 시행령23조①13호
금칙어: 무료 상담, 할인 이벤트, 특별 할인, 무료 체험

구현 방식:
- 금칙어는 리스트/딕셔너리로 관리 (하드코딩 OK, 나중에 DB로 이전 가능)
- 정규식으로 패턴 매칭 (예: r'[0-9]+kg\s*감량')
- 카테고리 4(부작용 누락)는 시술/한약 키워드 존재 + 부작용 언급 부재 조합 체크

## 코딩 규칙
- Python 3.11+, 타입 힌트, dataclass 사용
- 모든 함수에 docstring
- logging 모듈
- 테스트 가능하게 순수 함수로 설계

## 검증
python -c 'from src.utils.medical_ad_checker import check_violations; print(check_violations(\"이 시술은 확실한 효과가 있습니다\"))'
# → critical 위반 1건 이상 출력되어야 함

python -c 'from src.utils.exif import inject_exif; print(\"exif OK\")'
python -c 'from src.utils.naver_api import search_blog; print(\"naver OK\")'
"
