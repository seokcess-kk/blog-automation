"""
콘텐츠 생성 모듈 (generator).

키워드 분석 패턴을 기반으로 블로그 콘텐츠와 이미지를 생성합니다.

파이프라인:
1. prompt_builder: 시스템/유저 프롬프트 조립
2. content_generator: Claude API로 본문 생성
3. image_generator: Nano Banana Pro로 이미지 생성 + EXIF 삽입
"""

import logging
import re
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


def _insert_images_into_html(body_html: str, images: list[GeneratedImage]) -> str:
    """
    생성된 이미지를 본문 HTML의 h2 섹션 사이에 균등 삽입합니다.

    h2 태그 위치를 기준으로 이미지를 분산 배치합니다.
    첫 번째 이미지는 첫 h2 앞, 나머지는 h2 섹션 사이에 삽입됩니다.
    """
    if not images:
        return body_html

    # h2 태그 위치 찾기
    h2_positions = [m.start() for m in re.finditer(r"<h2[^>]*>", body_html)]

    if not h2_positions:
        # h2가 없으면 본문 끝에 모두 추가
        img_html = "\n".join(_make_img_tag(img) for img in images)
        return body_html + img_html

    # 삽입 지점 계산: h2 사이에 이미지를 균등 분배
    # 첫 이미지는 첫 h2 앞, 나머지는 h2 앞에 삽입
    insert_points: list[int] = []
    if len(images) <= len(h2_positions):
        # 이미지 수 <= h2 수: 균등 간격으로 배치
        step = max(1, len(h2_positions) // len(images))
        for i in range(len(images)):
            idx = min(i * step, len(h2_positions) - 1)
            insert_points.append(h2_positions[idx])
    else:
        # 이미지 수 > h2 수: 각 h2 앞에 하나씩, 남은 건 마지막 h2 뒤에 분산 배치
        insert_points = list(h2_positions)
        remaining = len(images) - len(h2_positions)
        last_h2_pos = h2_positions[-1]
        body_after = len(body_html) - last_h2_pos
        spacing = body_after // (remaining + 1) if remaining > 0 else 0
        for j in range(1, remaining + 1):
            insert_points.append(last_h2_pos + spacing * j)

    # 뒤에서부터 삽입 (위치가 밀리지 않도록)
    paired = list(zip(insert_points, images))
    paired.sort(key=lambda x: x[0], reverse=True)

    for pos, img in paired:
        img_tag = _make_img_tag(img)
        body_html = body_html[:pos] + img_tag + body_html[pos:]

    return body_html


def _make_img_tag(img: GeneratedImage) -> str:
    """이미지 HTML 태그를 생성합니다."""
    filename = img.get("filename", "")
    alt_text = (img.get("prompt", "") or "")[:100]
    return f'\n<div class="se-image"><img src="../images/{filename}" alt="{alt_text}"></div>\n'


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

    # Step 4: 이미지를 본문 HTML에 삽입
    body_html = content["body_html"]
    if images:
        body_html = _insert_images_into_html(body_html, images)
        logger.info(f"Step 4: Inserted {len(images)} images into body HTML")

    result = ContentResult(
        title=content["title"],
        meta_description=content["meta_description"],
        body_html=body_html,
        tags=content["tags"],
        images=images,
    )

    logger.info(
        f"Content generation complete: "
        f"title='{result['title'][:50]}...', "
        f"images={len(result['images'])}"
    )

    return result
