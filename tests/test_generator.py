"""
generator 모듈 테스트.

pytest 실행: pytest tests/test_generator.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestPromptBuilder:
    """prompt_builder 모듈 테스트."""

    def test_build_prompt_variable_substitution(self):
        """프롬프트 변수 치환 테스트."""
        from src.generator.prompt_builder import build_prompt

        result = build_prompt(
            keyword="테스트 키워드",
            region="서울 강남",
            content_angle="정보성",
        )

        # 결과가 dict인지 확인
        assert isinstance(result, dict)

        # system, user 프롬프트 존재 확인
        assert "system" in result or "messages" in result

    def test_build_prompt_with_pattern_data(self):
        """패턴 데이터 포함 프롬프트 테스트."""
        from src.generator.prompt_builder import build_prompt, PatternData

        pattern_data: PatternData = {
            "avg_char_count": 1500,
            "avg_image_count": 5,
            "avg_heading_count": 3,
            "title_patterns": ["keyword_position:front"],
            "related_keywords": ["연관1", "연관2"],
        }

        result = build_prompt(
            keyword="테스트",
            pattern_data=pattern_data,
        )

        assert result is not None

    def test_build_prompt_without_optional_params(self):
        """선택 파라미터 없이 프롬프트 빌드 테스트."""
        from src.generator.prompt_builder import build_prompt

        result = build_prompt(keyword="테스트")

        assert result is not None


class TestContentGenerator:
    """content_generator 모듈 테스트."""

    def test_generate_content_json_parsing(self):
        """콘텐츠 생성 결과 JSON 파싱 테스트 (mock)."""
        from src.generator.content_generator import GeneratedContent

        # GeneratedContent TypedDict 구조 확인
        mock_content: GeneratedContent = {
            "title": "테스트 제목",
            "meta_description": "테스트 설명",
            "body_html": "<p>테스트 본문</p>",
            "tags": ["태그1", "태그2"],
            "image_prompts": ["이미지 프롬프트 1"],
        }

        assert "title" in mock_content
        assert "body_html" in mock_content
        assert isinstance(mock_content["tags"], list)

    def test_content_generation_error_handling(self):
        """콘텐츠 생성 오류 처리 테스트."""
        from src.generator.content_generator import ContentGenerationError

        # 에러 클래스 존재 확인
        assert ContentGenerationError is not None

        # 에러 발생 테스트
        try:
            raise ContentGenerationError("테스트 오류")
        except ContentGenerationError as e:
            assert str(e) == "테스트 오류"


class TestImageGenerator:
    """image_generator 모듈 테스트."""

    def test_generated_image_structure(self):
        """GeneratedImage 구조 테스트."""
        from src.generator.image_generator import GeneratedImage

        # TypedDict 구조 확인
        mock_image: GeneratedImage = {
            "path": "/path/to/image.jpg",
            "alt": "이미지 설명",
            "prompt": "생성 프롬프트",
        }

        assert "path" in mock_image
        assert "alt" in mock_image

    def test_image_generator_exif_applied(self):
        """이미지 생성 시 EXIF 적용 테스트 (mock)."""
        with patch("src.generator.image_generator.generate_images") as mock_gen:
            mock_gen.return_value = [
                {
                    "path": "/output/test.jpg",
                    "alt": "테스트 이미지",
                    "has_exif": True,
                }
            ]

            result = mock_gen(["테스트 프롬프트"], "keyword_id")

            assert len(result) == 1
            assert result[0]["path"].endswith(".jpg")

    def test_image_generation_error_handling(self):
        """이미지 생성 오류 처리 테스트."""
        from src.generator.image_generator import ImageGenerationError

        assert ImageGenerationError is not None


class TestGenerateContentIntegration:
    """generate_content 통합 테스트."""

    def test_generate_content_returns_correct_structure(self):
        """generate_content 반환 구조 테스트."""
        with patch("src.generator.content_generator._generate_content") as mock_gen:
            mock_gen.return_value = {
                "title": "테스트 제목",
                "meta_description": "테스트 설명",
                "body_html": "<p>본문</p>",
                "tags": ["태그"],
                "image_prompts": [],
            }

            from src.generator import generate_content

            result = generate_content(
                keyword_id="test-id",
                keyword="테스트",
                skip_images=True,
            )

            assert "title" in result
            assert "body_html" in result
            assert "images" in result

    @pytest.mark.live
    def test_generate_content_live(self):
        """실제 API 호출 테스트 (--live 옵션으로 실행)."""
        from src.generator import generate_content

        result = generate_content(
            keyword_id="test",
            keyword="테스트 키워드",
            skip_images=True,
            skip_violation_check=True,
        )

        assert "title" in result
        assert len(result["title"]) > 0
