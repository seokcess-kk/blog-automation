"""
콘텐츠 생성 모듈 (generator).

키워드 분석 패턴을 기반으로 블로그 콘텐츠와 이미지를 생성합니다.

파이프라인:
1. prompt_builder: 시스템/유저 프롬프트 조립
2. content_generator: Claude API로 본문 생성
3. image_generator: Nano Banana Pro로 이미지 생성 + EXIF 삽입
"""

import logging
from typing import Any, TypedDict

from src.generator.prompt_builder import build_prompt, PatternData
from src.generator.content_generator import (
    generate_content as _generate_content,
    GeneratedContent,
    ContentGenerationError,
)
from src.generator.image_generator import (
    generate_images,
    GeneratedImage,
    ImageGenerationError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "generate_content",
    "build_prompt",
    "GeneratedContent",
    "GeneratedImage",
    "ContentGenerationError",
    "ImageGenerationError",
    "PatternData",
]


class ContentResult(TypedDict):
    """generate_content 전체 결과."""
    title: str
    meta_description: str
    body_html: str
    tags: list[str]
    images: list[GeneratedImage]


def generate_content(
    keyword_id: str,
    keyword: str | None = None,
    region: str | None = None,
    content_angle: str | None = None,
    pattern_data: PatternData | None = None,
    region_gps: tuple[float, float] | None = None,
    skip_images: bool = False,
    skip_violation_check: bool = False,
) -> ContentResult:
    """
    키워드 기반 블로그 콘텐츠를 생성합니다.

    전체 파이프라인:
    1. 프롬프트 빌드 (prompt_builder)
    2. 콘텐츠 생성 (content_generator - Claude API)
    3. 이미지 생성 (image_generator - Nano Banana Pro)

    Args:
        keyword_id: 키워드 ID (DB 참조용, 파일명 생성용)
        keyword: 타겟 키워드. None이면 keyword_id 사용.
        region: 타겟 지역 (선택)
        content_angle: 콘텐츠 방향 (선택)
        pattern_data: 상위노출 패턴 분석 데이터 (선택)
        region_gps: GPS 좌표 (EXIF 삽입용, 선택)
        skip_images: 이미지 생성 스킵 여부
        skip_violation_check: 의료광고법 검증 스킵 여부

    Returns:
        ContentResult: 생성된 콘텐츠 및 이미지 정보

    Raises:
        ContentGenerationError: 콘텐츠 생성 실패 시
        ImageGenerationError: 이미지 생성 실패 시 (skip_images=False)
    """
    # 키워드 설정
    if keyword is None:
        keyword = keyword_id

    logger.info(f"Starting content generation pipeline for keyword: '{keyword}'")

    # Step 1: 프롬프트 빌드
    logger.info("Step 1: Building prompt...")
    prompt = build_prompt(
        keyword=keyword,
        region=region,
        content_angle=content_angle,
        pattern_data=pattern_data,
    )

    # Step 2: 콘텐츠 생성
    logger.info("Step 2: Generating content with Claude API...")
    content = _generate_content(
        prompt=prompt,
        skip_violation_check=skip_violation_check,
    )

    # Step 3: 이미지 생성 (최대 10개 제한)
    MAX_IMAGES = 10
    images: list[GeneratedImage] = []
    if not skip_images and content.get("image_prompts"):
        image_prompts = content["image_prompts"][:MAX_IMAGES]
        if len(content["image_prompts"]) > MAX_IMAGES:
            logger.warning(
                f"Image prompts truncated: {len(content['image_prompts'])} → {MAX_IMAGES}"
            )
        logger.info(f"Step 3: Generating {len(image_prompts)} images with Nano Banana Pro...")
        try:
            images = generate_images(
                prompts=image_prompts,
                keyword_id=keyword_id,
                region_gps=region_gps,
            )
        except ImageGenerationError as e:
            logger.error(f"Image generation failed: {e}")
            # 이미지 생성 실패해도 콘텐츠는 반환
    else:
        logger.info("Step 3: Skipping image generation")

    result = ContentResult(
        title=content["title"],
        meta_description=content["meta_description"],
        body_html=content["body_html"],
        tags=content["tags"],
        images=images,
    )

    logger.info(
        f"Content generation complete: "
        f"title='{result['title'][:50]}...', "
        f"images={len(result['images'])}"
    )

    return result
