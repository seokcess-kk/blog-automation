#!/bin/bash
# skill-activation-prompt.sh
# Hook: UserPromptSubmit
# 사용자 프롬프트 제출 시 관련 스킬 자동 활성화 안내

# 입력: stdin으로 JSON 형태의 프롬프트 정보
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty')

# 스킬 활성화 키워드 체크
SKILLS_TO_ACTIVATE=()

# 1. medical-ad-law (의료 관련 키워드)
if echo "$PROMPT" | grep -qiE "의료|병원|치료|시술|한의원|건강|다이어트|피부과|성형|한약|클리닉"; then
    SKILLS_TO_ACTIVATE+=("medical-ad-law")
fi

# 2. scrapling-guidelines (크롤링 관련 키워드)
if echo "$PROMPT" | grep -qiE "scrapling|크롤링|수집|파싱|StealthyFetcher|serp|상위노출.*분석"; then
    SKILLS_TO_ACTIVATE+=("scrapling-guidelines")
fi

# 3. playwright-guidelines (발행 관련 키워드)
if echo "$PROMPT" | grep -qiE "playwright|발행|에디터|로그인|자동화|publish|browser"; then
    SKILLS_TO_ACTIVATE+=("playwright-guidelines")
fi

# 4. naver-seo (SEO 관련 키워드)
if echo "$PROMPT" | grep -qiE "SEO|상위노출|키워드|제목|태그|네이버|블로그.*최적화"; then
    SKILLS_TO_ACTIVATE+=("naver-seo")
fi

# 활성화할 스킬이 있으면 출력
if [ ${#SKILLS_TO_ACTIVATE[@]} -gt 0 ]; then
    echo "---"
    echo "[Skill Activation] 다음 스킬이 활성화됩니다:"
    for skill in "${SKILLS_TO_ACTIVATE[@]}"; do
        echo "  - $skill"
    done
    echo "---"
fi

exit 0
