#!/bin/bash
# build-check.sh
# Hook: Stop (수동 테스트 후 등록)
# 빌드 및 테스트 검증

# 종료 코드
# 0: 성공 (계속 진행)
# 1: 실패 (작업 중단)

echo "---"
echo "[Build Check] 빌드 검증을 시작합니다..."
echo "---"

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(dirname "$0")/../../.."
cd "$PROJECT_ROOT" || exit 1

# 1. Python 구문 검사
echo "[1/4] Python 구문 검사..."
if [ -d "src" ]; then
    python -m py_compile src/**/*.py 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[Error] Python 구문 오류가 발견되었습니다."
        exit 1
    fi
    echo "  ✓ Python 구문 검사 통과"
else
    echo "  ⏭ src 디렉토리 없음 (스킵)"
fi

# 2. 타입 힌트 검사 (mypy)
echo "[2/4] 타입 힌트 검사..."
if command -v mypy &> /dev/null && [ -d "src" ]; then
    mypy src --ignore-missing-imports --no-error-summary 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[Warning] 타입 힌트 오류가 있습니다. (경고만)"
    else
        echo "  ✓ 타입 힌트 검사 통과"
    fi
else
    echo "  ⏭ mypy 미설치 또는 src 없음 (스킵)"
fi

# 3. 의료광고법 금칙어 검사
echo "[3/4] 의료광고법 금칙어 검사..."
FORBIDDEN_WORDS="완치|100%|최고|최초|유일|기적의|부작용 없는"

if [ -d "prompts" ]; then
    VIOLATIONS=$(grep -rniE "$FORBIDDEN_WORDS" prompts/ 2>/dev/null)
    if [ -n "$VIOLATIONS" ]; then
        echo "[Error] 의료광고법 금칙어가 발견되었습니다:"
        echo "$VIOLATIONS"
        echo ""
        echo "해당 표현을 수정해주세요."
        exit 1
    fi
    echo "  ✓ 금칙어 검사 통과"
else
    echo "  ⏭ prompts 디렉토리 없음 (스킵)"
fi

# 4. 테스트 실행 (선택적)
echo "[4/4] 테스트 실행..."
if [ -d "tests" ] && command -v pytest &> /dev/null; then
    # 빠른 테스트만 실행 (-x: 첫 실패 시 중단)
    pytest tests/ -x -q --tb=no 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[Error] 테스트가 실패했습니다."
        echo "  상세 로그: pytest tests/ -v"
        exit 1
    fi
    echo "  ✓ 테스트 통과"
else
    echo "  ⏭ tests 디렉토리 또는 pytest 없음 (스킵)"
fi

echo ""
echo "---"
echo "[Build Check] 모든 검증을 통과했습니다. ✓"
echo "---"

exit 0
