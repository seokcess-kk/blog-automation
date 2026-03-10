#!/bin/bash
# post-tool-use-tracker.sh
# Hook: PostToolUse
# 도구 사용 후 추적 및 검증

# 입력: stdin으로 JSON 형태의 도구 사용 정보
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // empty')
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.output // empty')

# 로그 디렉토리 생성
LOG_DIR="./dev/active/logs"
mkdir -p "$LOG_DIR"

# 타임스탬프
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="$LOG_DIR/tool-usage-$(date +%Y%m%d).log"

# 도구 사용 로깅
echo "[$TIMESTAMP] Tool: $TOOL_NAME | File: $FILE_PATH" >> "$LOG_FILE"

# 파일 변경 추적 (Write, Edit 도구)
if [[ "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "Edit" ]]; then
    # 변경된 파일 경로 기록
    CHANGES_FILE="$LOG_DIR/changes-$(date +%Y%m%d).txt"
    echo "$FILE_PATH" >> "$CHANGES_FILE"

    # 의료 관련 파일 변경 시 경고
    if echo "$FILE_PATH" | grep -qiE "generator|prompt|medical"; then
        echo "---"
        echo "[Warning] 의료 콘텐츠 관련 파일이 변경되었습니다."
        echo "  파일: $FILE_PATH"
        echo "  medical-ad-law 스킬 검증이 필요합니다."
        echo "---"
    fi

    # publisher 관련 파일 변경 시 알림
    if echo "$FILE_PATH" | grep -qiE "publisher|editor|stealth"; then
        echo "---"
        echo "[Notice] 발행 관련 파일이 변경되었습니다."
        echo "  파일: $FILE_PATH"
        echo "  테스트 실행을 권장합니다: pytest tests/test_publisher.py"
        echo "---"
    fi
fi

# Bash 도구 사용 시 위험 명령어 체크
if [[ "$TOOL_NAME" == "Bash" ]]; then
    COMMAND=$(echo "$INPUT" | jq -r '.command // empty')

    # 위험 명령어 패턴
    if echo "$COMMAND" | grep -qiE "rm -rf|drop table|truncate|delete from"; then
        echo "---"
        echo "[Alert] 위험한 명령어가 실행되었습니다!"
        echo "  명령어: $COMMAND"
        echo "---"
    fi
fi

exit 0
