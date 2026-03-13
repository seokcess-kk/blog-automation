"""
콘텐츠 생성 모듈.

Claude API를 사용하여 블로그 콘텐츠를 생성합니다.
의료광고법 검증을 수행하고, 위반 시 수정 재요청합니다.
"""

import json
import logging
import re
import time
from typing import Any, TypedDict

import anthropic

from src import config
from src.generator.prompt_builder import PromptResult
from src.utils.medical_ad_checker import check_violations, get_violation_summary, has_critical

logger = logging.getLogger(__name__)

# 재시도 설정
MAX_PARSE_RETRIES = 2
MAX_VIOLATION_RETRIES = 2
MAX_TOTAL_RETRIES = 10  # 전체 루프 최대 반복 횟수
RATE_LIMIT_BACKOFF = [5, 10, 30, 60]  # 초 단위


class GeneratedContent(TypedDict):
    """생성된 콘텐츠 타입."""
    title: str
    meta_description: str
    body_html: str
    tags: list[str]
    image_prompts: list[str]


class ContentGenerationError(Exception):
    """콘텐츠 생성 오류."""
    pass


def _create_client() -> anthropic.Anthropic:
    """Anthropic 클라이언트 생성."""
    if not config.ANTHROPIC_API_KEY:
        raise ContentGenerationError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _extract_json_from_response(text: str) -> dict[str, Any] | None:
    """
    응답 텍스트에서 JSON을 추출합니다.

    Args:
        text: API 응답 텍스트

    Returns:
        파싱된 JSON 딕셔너리 또는 None
    """
    # 1. 먼저 전체 텍스트가 JSON인지 시도
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. ```json ... ``` 블록 추출
    json_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(json_block_pattern, text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # 3. { ... } 블록 추출 (가장 큰 것)
    brace_pattern = r"\{[\s\S]*\}"
    matches = re.findall(brace_pattern, text)
    for match in sorted(matches, key=len, reverse=True):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    return None


def _validate_content_structure(data: dict[str, Any]) -> GeneratedContent:
    """
    콘텐츠 구조를 검증하고 타입 변환합니다.

    Args:
        data: 파싱된 JSON 데이터

    Returns:
        GeneratedContent 타입으로 변환된 데이터

    Raises:
        ValueError: 필수 필드가 없는 경우
    """
    required_fields = ["title", "body_html"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    return GeneratedContent(
        title=str(data.get("title", "")),
        meta_description=str(data.get("meta_description", "")),
        body_html=str(data.get("body_html", "")),
        tags=list(data.get("tags", [])),
        image_prompts=list(data.get("image_prompts", [])),
    )


def _call_claude_api(
    client: anthropic.Anthropic,
    prompt: PromptResult,
    retry_count: int = 0,
) -> str:
    """
    Claude API를 호출합니다. Rate limit 시 exponential backoff.

    Args:
        client: Anthropic 클라이언트
        prompt: 시스템/유저 프롬프트
        retry_count: 현재 재시도 횟수

    Returns:
        API 응답 텍스트
    """
    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
            temperature=config.CLAUDE_TEMPERATURE,
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ],
        )

        # 텍스트 응답 추출
        if response.content and len(response.content) > 0:
            return response.content[0].text

        raise ContentGenerationError("Empty response from API")

    except anthropic.RateLimitError as e:
        if retry_count >= len(RATE_LIMIT_BACKOFF):
            raise ContentGenerationError(f"Rate limit exceeded after retries: {e}")

        wait_time = RATE_LIMIT_BACKOFF[retry_count]
        logger.warning(f"Rate limit hit, waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        return _call_claude_api(client, prompt, retry_count + 1)

    except anthropic.APIError as e:
        raise ContentGenerationError(f"API error: {e}")


def generate_content(
    prompt: PromptResult,
    skip_violation_check: bool = False,
) -> GeneratedContent:
    """
    Claude API를 사용하여 블로그 콘텐츠를 생성합니다.

    Args:
        prompt: 시스템/유저 프롬프트
        skip_violation_check: 의료광고법 검증 스킵 여부 (테스트용)

    Returns:
        GeneratedContent: 생성된 콘텐츠

    Raises:
        ContentGenerationError: 생성 실패 시
    """
    client = _create_client()
    current_prompt = prompt
    violation_retries = 0
    total_retries = 0

    while total_retries < MAX_TOTAL_RETRIES:
        total_retries += 1
        # API 호출
        logger.info("Calling Claude API for content generation...")
        response_text = _call_claude_api(client, current_prompt)

        # JSON 파싱 (재시도 로직)
        content_data = None
        parse_retries = 0

        while content_data is None and parse_retries <= MAX_PARSE_RETRIES:
            content_data = _extract_json_from_response(response_text)

            if content_data is None:
                parse_retries += 1
                if parse_retries > MAX_PARSE_RETRIES:
                    raise ContentGenerationError(
                        f"Failed to parse JSON after {MAX_PARSE_RETRIES} retries"
                    )

                logger.warning(f"JSON parse failed, requesting retry ({parse_retries})")
                retry_prompt = PromptResult(
                    system=prompt["system"],
                    user=(
                        "이전 응답에서 JSON 형식이 올바르지 않았습니다. "
                        "반드시 ```json ... ``` 블록 안에 유효한 JSON만 출력해주세요. "
                        "다른 텍스트 없이 JSON만 출력해주세요.\n\n"
                        f"원래 요청:\n{prompt['user']}"
                    ),
                )
                response_text = _call_claude_api(client, retry_prompt)

        # 구조 검증
        if content_data is None:
            raise ContentGenerationError("Failed to parse content data from API response")
        try:
            content = _validate_content_structure(content_data)
        except ValueError as e:
            raise ContentGenerationError(f"Invalid content structure: {e}")

        logger.info(f"Content generated: title='{content['title']}'")

        # 의료광고법 검증
        if skip_violation_check:
            return content

        full_text = f"{content['title']} {content['meta_description']} {content['body_html']}"
        violations = check_violations(full_text)

        if not has_critical(violations):
            if violations:  # warning만 있는 경우
                logger.warning(
                    f"Content has warnings: {get_violation_summary(violations)}"
                )
            return content

        # Critical 위반 발견 - 수정 재요청
        violation_retries += 1
        if violation_retries > MAX_VIOLATION_RETRIES:
            logger.error(
                f"Critical violations remain after {MAX_VIOLATION_RETRIES} retries. "
                "Manual review required."
            )
            raise ContentGenerationError(
                f"Medical ad law violations: {get_violation_summary(violations)}"
            )

        logger.warning(
            f"Critical violations found, requesting fix ({violation_retries})"
        )

        # 수정 프롬프트 생성
        violation_summary = get_violation_summary(violations)
        current_prompt = PromptResult(
            system=prompt["system"],
            user=(
                f"아래 콘텐츠에서 의료광고법 위반 사항이 발견되었습니다.\n\n"
                f"## 위반 내용\n{violation_summary}\n\n"
                f"## 현재 콘텐츠\n```json\n{json.dumps(content, ensure_ascii=False, indent=2)}\n```\n\n"
                f"위반 표현을 모두 수정하여 다시 JSON 형식으로 출력해주세요. "
                f"'도움이 될 수 있습니다', '개선 효과를 기대할 수 있습니다' 등 "
                f"안전한 표현으로 대체해주세요."
            ),
        )

    # MAX_TOTAL_RETRIES 초과 시
    raise ContentGenerationError(
        f"Content generation failed after {MAX_TOTAL_RETRIES} total retries"
    )
