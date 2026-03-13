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

from bs4 import BeautifulSoup

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
    "_insert_images_into_html",
]


def _insert_images_into_html(body_html: str, images: list[GeneratedImage]) -> str:
    """
    생성된 이미지를 본문 HTML의 블록 요소 사이에 안전하게 삽입합니다.

    삽입 규칙:
    1. h2 태그 직전 (단락 경계)에 삽입
    2. h2가 부족하면 p 태그 사이에 균등 분산
    3. 절대로 인라인(문장 중간)에 삽입하지 않음
    """
    if not images:
        return body_html

    soup = BeautifulSoup(body_html, "html.parser")

    # 블록 레벨 요소 수집 (h2, h3, p, ul, ol, div 등)
    block_elements = soup.find_all(['h2', 'h3', 'p', 'ul', 'ol', 'div', 'blockquote'])

    if not block_elements:
        # 블록 요소가 없으면 맨 뒤에 추가
        for img in images:
            img_tag = _create_image_soup(img)
            soup.append(img_tag)
        return str(soup)

    # h2 태그 위치 수집
    h2_elements = soup.find_all('h2')

    # 삽입 지점 결정: h2 직전 또는 p 태그 사이
    insert_positions: list[tuple[str, Any]] = []

    if h2_elements:
        # h2가 있으면 h2 직전에 삽입
        for h2 in h2_elements:
            insert_positions.append(('before', h2))

    # 이미지가 삽입 지점보다 많으면 p 태그 사이에 분산
    if len(images) > len(insert_positions):
        p_elements = [el for el in block_elements if el.name == 'p']
        remaining = len(images) - len(insert_positions)

        if p_elements and remaining > 0:
            step = max(1, len(p_elements) // (remaining + 1))
            for i in range(remaining):
                idx = min((i + 1) * step, len(p_elements) - 1)
                insert_positions.append(('after', p_elements[idx]))

    # 삽입 지점이 부족하면 마지막 블록 요소 뒤에 추가
    while len(insert_positions) < len(images):
        insert_positions.append(('after', block_elements[-1]))

    # 이미지 삽입 (역순으로 처리하여 DOM 변경 시 위치 영향 최소화)
    for i in range(len(images) - 1, -1, -1):
        img = images[i]
        if i < len(insert_positions):
            position_type, element = insert_positions[i]
            img_tag = _create_image_soup(img)

            if position_type == 'before':
                element.insert_before(img_tag)
            else:
                element.insert_after(img_tag)

    return str(soup)


def _create_image_soup(img: GeneratedImage):
    """BeautifulSoup용 이미지 태그를 생성합니다."""
    filename = img.get("filename", "")
    alt_text = (img.get("prompt", "") or "")[:100]
    # alt 텍스트에서 HTML 특수문자 이스케이프
    alt_text = alt_text.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    img_html = f'<div class="se-image"><img src="../images/{filename}" alt="{alt_text}"/></div>'
    return BeautifulSoup(img_html, "html.parser")


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
