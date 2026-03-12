"""
Gemini Flash 기반 심층 분석 모듈.

상위노출 블로그의 본문 내용, 문체, 전개 방식, 이미지 배치 전략을
Gemini 2.0 Flash로 분석하여 콘텐츠 생성 프롬프트의 품질을 높입니다.

비용: 블로그당 ~3000 입력 + ~1000 출력 토큰 x 6회 = ~$0.004/키워드
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src import config
from src.analyzer.content_parser import ParsedContent

logger = logging.getLogger(__name__)


@dataclass
class BlogDeepAnalysis:
    """단일 블로그 심층 분석 결과."""

    url: str
    title: str
    writing_tone: str
    """문체: '대화체', '정보형', '전문적' 등"""

    sentence_style: str
    """문장 스타일: '짧은 문장 위주', '설명 위주' 등"""

    opening_strategy: str
    """도입 전략: '질문형', '경험담', '팩트 제시' 등"""

    closing_strategy: str
    """마무리 전략: 'CTA', '요약', '감성 마무리' 등"""

    section_flow: list[dict[str, Any]]
    """[{"heading": "...", "role": "도입/본론/결론", "char_ratio": 0.2}]"""

    content_type: str
    """콘텐츠 유형: '리뷰형', '정보형', '비교형', '가이드형' 등"""

    image_placement: list[dict[str, Any]]
    """[{"position": "h2 직후", "purpose": "시각적 도입", "count": 1}]"""

    keyword_usage_style: str
    """키워드 자연스러운 활용법"""

    key_phrases: list[str]
    """인상적인 표현 5~10개"""

    main_topics: list[dict[str, str]] = field(default_factory=list)
    """[{"topic": "토픽명", "description": "설명"}] - 이 글이 다루는 주요 주제/토픽"""

    competitor_brands: list[str] = field(default_factory=list)
    """감지된 경쟁사 브랜드명 (한의원, 클리닉, 병원 등)"""

    informational_content: str = ""
    """경쟁사 브랜드 제외한 순수 정보성 내용 요약"""


@dataclass
class AggregatedDeepAnalysis:
    """종합 심층 분석 결과 (여러 블로그 합산)."""

    dominant_tone: str
    """지배적 문체"""

    common_structure: str
    """공통 전개 구조"""

    image_strategy: str
    """종합 이미지 배치 전략"""

    recommended_sections: list[dict[str, Any]]
    """추천 섹션 구성"""

    writing_guidelines: str
    """종합 작성 가이드라인"""

    source_analyses: list[BlogDeepAnalysis] = field(default_factory=list)
    """개별 블로그 분석 결과"""

    common_topics: list[dict[str, Any]] = field(default_factory=list)
    """[{"topic": "토픽명", "frequency": 4, "recommended_coverage": "필수/권장"}] - 공통 토픽"""

    filtered_competitors: list[str] = field(default_factory=list)
    """제외할 경쟁사 브랜드 목록 (전체 블로그에서 감지된 브랜드 병합)"""

    topic_outline: str = ""
    """정보성 원고 토픽 구성 제안"""


def _build_single_blog_prompt(content: ParsedContent, keyword: str) -> str:
    """단일 블로그 분석용 프롬프트를 생성합니다."""
    sections_text = ""
    if content.sections:
        for s in content.sections:
            section_text = s.text[:500] if len(s.text) > 500 else s.text
            heading_label = f"[{s.heading_tag}] {s.heading}" if s.heading else "[도입부]"
            img_info = f" (이미지 {s.image_count}개)" if s.image_count > 0 else ""
            sections_text += f"\n### {heading_label}{img_info}\n{section_text}\n"
    elif content.full_text:
        # fallback: sections가 비어있으면 full_text 앞부분 전달
        sections_text = f"\n### [전체 본문]\n{content.full_text[:2000]}\n"

    return f"""다음은 네이버 블로그에서 "{keyword}" 키워드로 상위노출된 글입니다.
이 글의 문체, 전개 방식, 이미지 배치 전략, 그리고 다루는 주요 토픽을 분석해주세요.

## 블로그 정보
- 제목: {content.title}
- 총 글자수: {content.char_count}
- 이미지 수: {content.image_count}
- 소제목 수: {content.heading_count}

## 섹션별 구조
{sections_text}

## 분석 요청
위 블로그 글을 분석하여 아래 JSON 형식으로 응답해주세요:

{{
    "writing_tone": "문체 (대화체/정보형/전문적/친근한 등)",
    "sentence_style": "문장 스타일 (짧은 문장 위주/설명 위주/혼합형 등)",
    "opening_strategy": "도입 전략 (질문형/경험담/팩트 제시/공감 유도 등)",
    "closing_strategy": "마무리 전략 (CTA/요약/감성 마무리/추천 등)",
    "section_flow": [
        {{"heading": "섹션명", "role": "도입/본론/결론/부가정보", "char_ratio": 0.2}}
    ],
    "content_type": "콘텐츠 유형 (리뷰형/정보형/비교형/가이드형/경험담 등)",
    "image_placement": [
        {{"position": "위치 설명", "purpose": "이미지 목적", "count": 1}}
    ],
    "keyword_usage_style": "키워드 활용 방식 설명",
    "key_phrases": ["인상적인 표현 5~10개"],
    "main_topics": [
        {{"topic": "주요 토픽/주제명", "description": "이 토픽에서 다루는 핵심 내용 요약"}}
    ],
    "competitor_brands": ["글에서 언급된 특정 브랜드/업체/한의원/클리닉/병원 이름 (있으면)"],
    "informational_content": "특정 브랜드 홍보 내용을 제외한 순수 정보성 내용 요약 (1~2문장)"
}}

## 토픽 분석 가이드
- main_topics: 이 글이 다루는 핵심 주제들 (예: "다이어트 원리", "체질 분석", "시술 과정", "효과와 주의사항" 등)
- competitor_brands: 특정 업체/브랜드명이 있다면 추출 (일반 명사인 "한의원", "병원"은 제외, "XX한의원", "YY클리닉" 같은 고유명사만)
- informational_content: 브랜드 광고가 아닌, 독자에게 유용한 정보 부분만 요약"""


def _build_aggregation_prompt(analyses: list[BlogDeepAnalysis], keyword: str) -> str:
    """종합 분석용 프롬프트를 생성합니다."""
    summaries = []
    all_topics = []
    all_competitors = []

    for i, a in enumerate(analyses, 1):
        # 토픽 수집
        all_topics.extend(a.main_topics)
        all_competitors.extend(a.competitor_brands)

        topics_str = ", ".join([t.get("topic", "") for t in a.main_topics]) if a.main_topics else "없음"
        competitors_str = ", ".join(a.competitor_brands) if a.competitor_brands else "없음"

        summaries.append(f"""### 블로그 {i}: {a.title}
- 문체: {a.writing_tone}
- 문장: {a.sentence_style}
- 도입: {a.opening_strategy}
- 마무리: {a.closing_strategy}
- 유형: {a.content_type}
- 이미지 배치: {json.dumps(a.image_placement, ensure_ascii=False)}
- 키워드 활용: {a.keyword_usage_style}
- 주요 토픽: {topics_str}
- 감지된 브랜드: {competitors_str}
- 정보성 내용: {a.informational_content or '없음'}""")

    analyses_text = "\n\n".join(summaries)

    # 수집된 토픽/경쟁사 목록 전달
    collected_topics = list(set([t.get("topic", "") for t in all_topics if t.get("topic")]))
    collected_competitors = list(set(all_competitors))

    return f"""다음은 "{keyword}" 키워드의 네이버 상위노출 블로그 {len(analyses)}개를 각각 분석한 결과입니다.
이들의 공통 패턴을 종합하여 새로운 블로그 글 작성 가이드라인을 만들어주세요.

{analyses_text}

## 수집된 토픽 목록 (빈도 분석 필요)
{json.dumps(collected_topics, ensure_ascii=False)}

## 감지된 경쟁사 브랜드 (제외 대상)
{json.dumps(collected_competitors, ensure_ascii=False)}

## 종합 분석 요청
위 분석 결과를 종합하여 아래 JSON 형식으로 응답해주세요:

{{
    "dominant_tone": "지배적 문체 (가장 많이 사용되는 톤)",
    "common_structure": "공통 전개 구조 (도입→본론→결론 등 상세 설명)",
    "image_strategy": "종합 이미지 배치 전략 (위치, 개수, 목적)",
    "recommended_sections": [
        {{"heading": "추천 소제목", "target_chars": 300, "image_count": 1, "role": "역할", "guidelines": "작성 지침"}}
    ],
    "writing_guidelines": "종합 작성 가이드라인 (문체, 어투, 핵심 포인트 등)",
    "common_topics": [
        {{"topic": "공통 토픽명", "frequency": 3, "recommended_coverage": "필수/권장/선택"}}
    ],
    "filtered_competitors": ["제외할 경쟁사 브랜드 목록"],
    "topic_outline": "정보성 원고 작성을 위한 토픽 구성 제안 (어떤 주제를 어떤 순서로 다룰지)"
}}

## 토픽 종합 가이드
- common_topics: 여러 블로그에서 공통으로 다루는 토픽을 빈도순으로 정리. frequency는 몇 개 블로그에서 언급되었는지.
- recommended_coverage: "필수"(3개 이상에서 언급), "권장"(2개에서 언급), "선택"(1개에서만 언급)
- filtered_competitors: 감지된 모든 경쟁사 브랜드 (새 원고 작성 시 절대 언급 금지)
- topic_outline: 정보성 원고 구성 제안 - 경쟁사 홍보가 아닌 순수 정보 전달 관점에서"""


def _call_gemini(prompt: str, max_retries: int = 3) -> dict[str, Any] | None:
    """Gemini API를 호출하여 JSON 응답을 파싱합니다. 429 시 exponential backoff."""
    if not config.GOOGLE_AI_API_KEY:
        logger.warning("GOOGLE_AI_API_KEY가 설정되지 않았습니다.")
        return None

    backoff_seconds = [10, 30, 60]

    for attempt in range(max_retries):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=config.GOOGLE_AI_API_KEY)
            response = client.models.generate_content(
                model=config.GEMINI_ANALYSIS_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    response_mime_type="application/json",
                ),
            )

            if not response or not response.text:
                logger.warning("Gemini 응답이 비어있습니다.")
                return None

            return json.loads(response.text)

        except json.JSONDecodeError as e:
            logger.error(f"Gemini JSON 파싱 오류: {e}")
            return None
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = backoff_seconds[attempt]
                logger.warning(f"Gemini 429 rate limit, {wait}초 후 재시도 ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            logger.error(f"Gemini API 호출 오류: {e}")
            return None

    return None


def analyze_blog_deep(
    parsed_content: ParsedContent,
    keyword: str,
) -> BlogDeepAnalysis | None:
    """
    단일 블로그를 Gemini Flash로 심층 분석합니다.

    Args:
        parsed_content: 파싱된 블로그 콘텐츠
        keyword: 분석 대상 키워드

    Returns:
        BlogDeepAnalysis 또는 None (실패 시)
    """
    if not parsed_content.sections and not parsed_content.full_text:
        logger.warning(f"섹션/본문 데이터 없음: {parsed_content.url}")
        return None

    prompt = _build_single_blog_prompt(parsed_content, keyword)
    result = _call_gemini(prompt)

    if not result:
        return None

    try:
        return BlogDeepAnalysis(
            url=parsed_content.url,
            title=parsed_content.title,
            writing_tone=result.get("writing_tone", "알 수 없음"),
            sentence_style=result.get("sentence_style", "알 수 없음"),
            opening_strategy=result.get("opening_strategy", "알 수 없음"),
            closing_strategy=result.get("closing_strategy", "알 수 없음"),
            section_flow=result.get("section_flow", []),
            content_type=result.get("content_type", "알 수 없음"),
            image_placement=result.get("image_placement", []),
            keyword_usage_style=result.get("keyword_usage_style", ""),
            key_phrases=result.get("key_phrases", []),
            main_topics=result.get("main_topics", []),
            competitor_brands=result.get("competitor_brands", []),
            informational_content=result.get("informational_content", ""),
        )
    except Exception as e:
        logger.error(f"BlogDeepAnalysis 생성 오류: {e}")
        return None


def analyze_blogs_deep(
    contents: list[ParsedContent],
    keyword: str,
    delay_seconds: float = 2.0,
) -> AggregatedDeepAnalysis | None:
    """
    여러 블로그를 심층 분석하고 종합 결과를 반환합니다.

    Args:
        contents: 파싱된 블로그 콘텐츠 목록
        keyword: 분석 대상 키워드
        delay_seconds: API 호출 간 대기 시간 (초)

    Returns:
        AggregatedDeepAnalysis 또는 None (실패 시)
    """
    if not contents:
        logger.warning("심층 분석할 콘텐츠가 없습니다.")
        return None

    logger.info(f"심층 분석 시작: {len(contents)}개 블로그, 키워드='{keyword}'")

    # 개별 블로그 분석
    analyses: list[BlogDeepAnalysis] = []
    for i, content in enumerate(contents):
        logger.info(f"  블로그 {i+1}/{len(contents)} 분석 중: {content.title[:30]}...")
        analysis = analyze_blog_deep(content, keyword)
        if analysis:
            analyses.append(analysis)
        else:
            logger.warning(f"  블로그 {i+1} 분석 실패: {content.url}")

        # API rate limit 대기 (마지막 호출 제외)
        if i < len(contents) - 1:
            time.sleep(delay_seconds)

    if not analyses:
        logger.warning("모든 블로그 심층 분석에 실패했습니다.")
        return None

    logger.info(f"개별 분석 완료: {len(analyses)}/{len(contents)}개 성공")

    # 종합 분석
    logger.info("종합 분석 중...")
    agg_prompt = _build_aggregation_prompt(analyses, keyword)
    agg_result = _call_gemini(agg_prompt)

    if not agg_result:
        # 종합 분석 실패 시 개별 결과만으로 기본 종합 생성
        logger.warning("종합 분석 실패, 개별 결과로 기본 종합 생성")
        # 개별 분석에서 토픽/경쟁사 수집
        all_topics = []
        all_competitors = []
        for a in analyses:
            all_topics.extend(a.main_topics)
            all_competitors.extend(a.competitor_brands)

        return AggregatedDeepAnalysis(
            dominant_tone=analyses[0].writing_tone if analyses else "알 수 없음",
            common_structure="개별 분석 참조",
            image_strategy="개별 분석 참조",
            recommended_sections=[],
            writing_guidelines="개별 분석 참조",
            source_analyses=analyses,
            common_topics=[{"topic": t.get("topic", ""), "frequency": 1, "recommended_coverage": "선택"} for t in all_topics],
            filtered_competitors=list(set(all_competitors)),
            topic_outline="개별 분석 참조",
        )

    try:
        return AggregatedDeepAnalysis(
            dominant_tone=agg_result.get("dominant_tone", "알 수 없음"),
            common_structure=agg_result.get("common_structure", ""),
            image_strategy=agg_result.get("image_strategy", ""),
            recommended_sections=agg_result.get("recommended_sections", []),
            writing_guidelines=agg_result.get("writing_guidelines", ""),
            source_analyses=analyses,
            common_topics=agg_result.get("common_topics", []),
            filtered_competitors=agg_result.get("filtered_competitors", []),
            topic_outline=agg_result.get("topic_outline", ""),
        )
    except Exception as e:
        logger.error(f"AggregatedDeepAnalysis 생성 오류: {e}")
        return None


def deep_analysis_to_dict(analysis: AggregatedDeepAnalysis) -> dict[str, Any]:
    """AggregatedDeepAnalysis를 딕셔너리로 변환합니다."""
    return {
        "dominant_tone": analysis.dominant_tone,
        "common_structure": analysis.common_structure,
        "image_strategy": analysis.image_strategy,
        "recommended_sections": analysis.recommended_sections,
        "writing_guidelines": analysis.writing_guidelines,
        "common_topics": analysis.common_topics,
        "filtered_competitors": analysis.filtered_competitors,
        "topic_outline": analysis.topic_outline,
        "source_analyses": [
            {
                "url": a.url,
                "title": a.title,
                "writing_tone": a.writing_tone,
                "sentence_style": a.sentence_style,
                "opening_strategy": a.opening_strategy,
                "closing_strategy": a.closing_strategy,
                "section_flow": a.section_flow,
                "content_type": a.content_type,
                "image_placement": a.image_placement,
                "keyword_usage_style": a.keyword_usage_style,
                "key_phrases": a.key_phrases,
                "main_topics": a.main_topics,
                "competitor_brands": a.competitor_brands,
                "informational_content": a.informational_content,
            }
            for a in analysis.source_analyses
        ],
    }
