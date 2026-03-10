"""
프롬프트 빌더 모듈.

prompts/ 디렉토리의 템플릿을 로드하고 변수를 치환하여
Claude API 호출용 프롬프트를 조립합니다.
"""

import logging
from pathlib import Path
from typing import Any, TypedDict

from src import config

logger = logging.getLogger(__name__)

# 프롬프트 디렉토리
PROMPTS_DIR = config.PROJECT_ROOT / "prompts"


class PromptResult(TypedDict):
    """프롬프트 빌더 결과 타입."""
    system: str
    user: str


class PatternData(TypedDict, total=False):
    """패턴 분석 데이터 타입."""
    avg_char_count: int
    avg_image_count: int
    avg_heading_count: int
    title_patterns: str | list[str]
    keyword_placement: str | dict[str, Any]
    related_keywords: str | list[str]
    content_structure: str | dict[str, Any]


def _load_template(filename: str) -> str:
    """
    프롬프트 템플릿 파일을 로드합니다.

    Args:
        filename: 템플릿 파일명 (예: 'system_prompt.md')

    Returns:
        템플릿 내용 문자열

    Raises:
        FileNotFoundError: 템플릿 파일이 없는 경우
    """
    template_path = PROMPTS_DIR / filename
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    logger.debug(f"Loaded template: {filename} ({len(content)} chars)")
    return content


def _format_list(data: str | list[str]) -> str:
    """리스트를 마크다운 목록 형식으로 변환합니다."""
    if isinstance(data, str):
        return data
    return "\n".join(f"- {item}" for item in data)


def _format_dict(data: str | dict[str, Any]) -> str:
    """딕셔너리를 마크다운 형식으로 변환합니다."""
    if isinstance(data, str):
        return data
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"- **{key}**: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)


def build_prompt(
    keyword: str,
    region: str | None = None,
    content_angle: str | None = None,
    pattern_data: PatternData | None = None,
) -> PromptResult:
    """
    콘텐츠 생성용 프롬프트를 조립합니다.

    System Prompt + Pattern Injection 템플릿을 로드하고,
    변수를 치환하여 최종 프롬프트를 생성합니다.

    Args:
        keyword: 타겟 키워드
        region: 타겟 지역 (선택)
        content_angle: 콘텐츠 방향/톤 (선택)
        pattern_data: 상위노출 패턴 분석 데이터 (선택)

    Returns:
        PromptResult: {'system': ..., 'user': ...} 형태의 프롬프트
    """
    logger.info(f"Building prompt for keyword: '{keyword}'")

    # 시스템 프롬프트 로드
    system_prompt = _load_template("system_prompt.md")

    # 패턴 인젝션 템플릿 로드
    pattern_template = _load_template("pattern_injection.md")

    # 기본값 설정
    if pattern_data is None:
        pattern_data = {}

    region = region or "전국"
    content_angle = content_angle or "정보 제공형"

    # 패턴 데이터 기본값
    avg_char_count = pattern_data.get("avg_char_count", 2000)
    avg_image_count = pattern_data.get("avg_image_count", 3)
    avg_heading_count = pattern_data.get("avg_heading_count", 4)
    title_patterns = pattern_data.get("title_patterns", "분석된 패턴 없음")
    keyword_placement = pattern_data.get("keyword_placement", "제목, 첫 문단, 소제목에 키워드 배치")
    related_keywords = pattern_data.get("related_keywords", "분석된 연관 키워드 없음")
    content_structure = pattern_data.get("content_structure", "서론-본론-결론 구조")

    # 변수 치환
    variables = {
        "{{keyword}}": keyword,
        "{{region}}": region,
        "{{content_angle}}": content_angle,
        "{{avg_char_count}}": str(avg_char_count),
        "{{avg_image_count}}": str(avg_image_count),
        "{{avg_heading_count}}": str(avg_heading_count),
        "{{title_patterns}}": _format_list(title_patterns),
        "{{keyword_placement}}": _format_dict(keyword_placement),
        "{{related_keywords}}": _format_list(related_keywords),
        "{{content_structure}}": _format_dict(content_structure),
    }

    user_prompt = pattern_template
    for placeholder, value in variables.items():
        user_prompt = user_prompt.replace(placeholder, value)

    # 최종 유저 프롬프트 (작성 요청 추가)
    user_prompt += f"\n\n---\n\n위 지침에 따라 '{keyword}' 키워드로 블로그 글을 작성해주세요."

    logger.info(
        f"Prompt built: system={len(system_prompt)} chars, user={len(user_prompt)} chars"
    )

    return PromptResult(
        system=system_prompt,
        user=user_prompt,
    )
