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
    source_titles: list[str]
    deep_analysis: dict[str, Any]
    brand_info: dict[str, Any]
    common_topics: list[dict[str, Any]]
    filtered_competitors: list[str]
    topic_outline: str


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


def _format_deep_analysis(deep: dict[str, Any]) -> str:
    """심층 분석 데이터를 프롬프트용 마크다운으로 변환합니다."""
    lines = []

    lines.append(f"**지배적 문체**: {deep.get('dominant_tone', '분석 없음')}")
    lines.append(f"**공통 전개 구조**: {deep.get('common_structure', '분석 없음')}")
    lines.append("")
    lines.append(f"**이미지 배치 전략**:")
    lines.append(deep.get("image_strategy", "분석 없음"))
    lines.append("")

    recommended = deep.get("recommended_sections", [])
    if recommended:
        lines.append("**추천 섹션 구성**:")
        for i, sec in enumerate(recommended, 1):
            heading = sec.get("heading", f"섹션 {i}")
            chars = sec.get("target_chars", "")
            img = sec.get("image_count", 0)
            role = sec.get("role", "")
            guidelines = sec.get("guidelines", "")
            lines.append(f"{i}. **{heading}** ({chars}자, 이미지 {img}개) - {role}")
            if guidelines:
                lines.append(f"   - {guidelines}")
        lines.append("")

    guidelines = deep.get("writing_guidelines", "")
    if guidelines:
        lines.append(f"**종합 작성 가이드라인**:")
        lines.append(guidelines)
        lines.append("")

    # 개별 블로그 분석 요약 (인상적인 표현)
    source_analyses = deep.get("source_analyses", [])
    all_phrases = []
    for sa in source_analyses:
        all_phrases.extend(sa.get("key_phrases", []))
    if all_phrases:
        lines.append("**상위노출 글의 인상적인 표현 (참고용)**:")
        for phrase in all_phrases[:15]:
            lines.append(f"- {phrase}")

    return "\n".join(lines)


def _format_topics(topics: list[dict[str, Any]]) -> str:
    """토픽 목록을 마크다운 형식으로 변환합니다."""
    if not topics:
        return "분석된 공통 토픽 없음"

    lines = []
    for t in topics:
        topic = t.get("topic", "")
        freq = t.get("frequency", 1)
        coverage = t.get("recommended_coverage", "선택")
        description = t.get("description", "")

        line = f"- **{topic}** [{coverage}]"
        if description:
            line += f": {description}"
        line += f" (빈도: {freq}개 블로그)"
        lines.append(line)

    return "\n".join(lines)


def _format_brand_info(brand: dict[str, Any]) -> str:
    """브랜드 정보를 프롬프트용 마크다운으로 변환합니다."""
    lines = []

    # 브랜드 요약
    summary = brand.get("summary", "")
    if summary:
        lines.append(f"**브랜드 요약**: {summary}")
        lines.append("")

    # 브랜드 톤
    tone = brand.get("brand_tone", "")
    if tone:
        tone_desc = {
            "professional": "전문적이고 신뢰감 있는",
            "friendly": "친근하고 따뜻한",
            "luxury": "고급스럽고 세련된",
            "innovative": "혁신적이고 미래지향적인",
            "traditional": "전통적이고 안정적인",
        }
        lines.append(f"**브랜드 톤**: {tone_desc.get(tone, tone)}")
        lines.append("")

    # 핵심 강점
    strengths = brand.get("extracted_strengths", [])
    if strengths and strengths != ["정보 없음"]:
        lines.append("**핵심 강점/차별점**:")
        for s in strengths[:5]:
            lines.append(f"- {s}")
        lines.append("")

    # 주요 서비스/제품
    services = brand.get("extracted_services", [])
    if services and services != ["정보 없음"]:
        lines.append("**주요 서비스/제품**:")
        for s in services[:5]:
            lines.append(f"- {s}")
        lines.append("")

    # 메인 페이지 정보 (간략)
    main_page = brand.get("main_page", {})
    if main_page.get("title"):
        lines.append(f"**홈페이지 제목**: {main_page.get('title', '')}")

    if not lines:
        return "브랜드 정보 없음"

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
    avg_image_count = min(pattern_data.get("avg_image_count", 3), 10)  # 최대 10개 제한
    avg_heading_count = pattern_data.get("avg_heading_count", 4)
    title_patterns = pattern_data.get("title_patterns", "분석된 패턴 없음")
    keyword_placement = pattern_data.get("keyword_placement", "제목, 첫 문단, 소제목에 키워드 배치")
    related_keywords = pattern_data.get("related_keywords", "분석된 연관 키워드 없음")
    content_structure = pattern_data.get("content_structure", "서론-본론-결론 구조")
    source_titles = pattern_data.get("source_titles", [])
    deep_analysis = pattern_data.get("deep_analysis")

    # 심층 분석 포맷팅
    deep_analysis_text = ""
    if deep_analysis:
        deep_analysis_text = _format_deep_analysis(deep_analysis)

    # 브랜드 정보 포맷팅
    brand_info = pattern_data.get("brand_info")
    brand_info_text = ""
    if brand_info and isinstance(brand_info, dict):
        brand_info_text = _format_brand_info(brand_info)

    # 토픽 정보 추출 (deep_analysis 또는 직접 전달된 값)
    common_topics = pattern_data.get("common_topics")
    if not common_topics and deep_analysis:
        common_topics = deep_analysis.get("common_topics", [])

    filtered_competitors = pattern_data.get("filtered_competitors")
    if not filtered_competitors and deep_analysis:
        filtered_competitors = deep_analysis.get("filtered_competitors", [])

    topic_outline = pattern_data.get("topic_outline")
    if not topic_outline and deep_analysis:
        topic_outline = deep_analysis.get("topic_outline", "")

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
        "{{source_titles}}": _format_list(source_titles) if source_titles else "분석된 제목 없음",
        "{{deep_analysis}}": deep_analysis_text if deep_analysis_text else "심층 분석 데이터 없음",
        "{{brand_info}}": brand_info_text if brand_info_text else "브랜드 정보 없음",
        "{{common_topics}}": _format_topics(common_topics) if common_topics else "분석된 공통 토픽 없음",
        "{{filtered_competitors}}": _format_list(filtered_competitors) if filtered_competitors else "제외할 경쟁사 없음",
        "{{topic_outline}}": topic_outline if topic_outline else "토픽 구성 제안 없음",
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
