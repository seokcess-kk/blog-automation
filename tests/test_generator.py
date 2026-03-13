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

    def test_build_prompt_with_deep_analysis(self):
        """심층 분석 데이터 포함 프롬프트 렌더링 테스트."""
        from src.generator.prompt_builder import build_prompt, PatternData

        pattern_data: PatternData = {
            "avg_char_count": 2000,
            "avg_image_count": 7,
            "avg_heading_count": 4,
            "title_patterns": ["keyword_position:front"],
            "related_keywords": ["식단", "운동"],
            "deep_analysis": {
                "dominant_tone": "대화체",
                "common_structure": "도입→정보→비교→CTA",
                "image_strategy": "H2 직후 관련 이미지 1개, 리뷰 섹션에 2~3개 집중",
                "recommended_sections": [
                    {"heading": "도입", "target_chars": 300, "image_count": 1, "role": "도입", "guidelines": "개인 경험"},
                    {"heading": "핵심 정보", "target_chars": 400, "image_count": 2, "role": "본론", "guidelines": "상세 설명"},
                ],
                "writing_guidelines": "친근한 대화체로 작성, ~거든요/~했어요 어미 사용",
                "source_analyses": [
                    {
                        "url": "https://blog.naver.com/test/1",
                        "title": "테스트",
                        "writing_tone": "대화체",
                        "sentence_style": "짧은 문장",
                        "opening_strategy": "경험담",
                        "closing_strategy": "CTA",
                        "section_flow": [],
                        "content_type": "리뷰형",
                        "image_placement": [],
                        "keyword_usage_style": "자연스럽게",
                        "key_phrases": ["직접 해봤는데", "정말 추천"],
                    },
                ],
            },
        }

        result = build_prompt(keyword="다이어트", pattern_data=pattern_data)

        assert result is not None
        # 심층 분석 내용이 user 프롬프트에 포함되어야 함
        assert "대화체" in result["user"]
        assert "도입→정보→비교→CTA" in result["user"]
        assert "H2 직후" in result["user"]
        assert "직접 해봤는데" in result["user"]
        # 기본 placeholder가 남아있지 않아야 함
        assert "{{deep_analysis}}" not in result["user"]


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

    def test_parse_style_realistic(self):
        """[realistic photo] 스타일 태그 파싱 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("[realistic photo] Interior of wellness center")
        assert style == "realistic"
        assert prompt == "Interior of wellness center"

    def test_parse_style_realistic_short(self):
        """[realistic] 스타일 태그 파싱 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("[realistic] Modern consultation room")
        assert style == "realistic"
        assert prompt == "Modern consultation room"

    def test_parse_style_illustration(self):
        """[illustration] 스타일 태그 파싱 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("[illustration] Weight loss concept diagram")
        assert style == "illustration"
        assert prompt == "Weight loss concept diagram"

    def test_parse_style_infographic(self):
        """[infographic] 스타일 태그 파싱 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("[infographic] Healthy lifestyle steps comparison")
        assert style == "infographic"
        assert prompt == "Healthy lifestyle steps comparison"

    def test_parse_style_default(self):
        """스타일 태그 없는 프롬프트 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("No style tag prompt")
        assert style == "default"
        assert prompt == "No style tag prompt"

    def test_parse_style_case_insensitive(self):
        """대소문자 무관 스타일 태그 파싱 테스트."""
        from src.generator.image_generator import _parse_style

        style, prompt = _parse_style("[REALISTIC PHOTO] Test image")
        assert style == "realistic"
        assert prompt == "Test image"

    def test_enhance_prompt_realistic_suffix(self):
        """realistic 스타일에 올바른 suffix가 적용되는지 테스트."""
        from src.generator.image_generator import _enhance_prompt, IMAGE_STYLE_SUFFIX

        result = _enhance_prompt("[realistic photo] Wellness center interior")
        assert "professional photography" in result
        assert "natural lighting" in result
        assert "illustration" not in result

    def test_enhance_prompt_illustration_suffix(self):
        """illustration 스타일에 올바른 suffix가 적용되는지 테스트."""
        from src.generator.image_generator import _enhance_prompt

        result = _enhance_prompt("[illustration] Body balance concept")
        assert "blog illustration" in result
        assert "clean design" in result

    def test_enhance_prompt_infographic_suffix(self):
        """infographic 스타일에 올바른 suffix가 적용되는지 테스트."""
        from src.generator.image_generator import _enhance_prompt

        result = _enhance_prompt("[infographic] Diet comparison chart")
        assert "infographic design" in result
        assert "data visualization" in result

    def test_enhance_prompt_default_suffix(self):
        """스타일 태그 없는 프롬프트에 기본 suffix가 적용되는지 테스트."""
        from src.generator.image_generator import _enhance_prompt

        result = _enhance_prompt("Simple prompt without style tag")
        assert "blog illustration" in result  # default는 illustration과 동일

    def test_enhance_prompt_skip_existing_suffix(self):
        """이미 suffix가 포함된 프롬프트는 그대로 반환하는지 테스트."""
        from src.generator.image_generator import _enhance_prompt

        prompt = "[realistic photo] Already has professional photography style"
        result = _enhance_prompt(prompt)
        # 기존 suffix가 있으면 추가하지 않음
        assert result.count("professional") == 1

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
        # __init__.py에서 _generate_content로 바인딩되므로 해당 위치를 mock
        with patch("src.generator._generate_content") as mock_gen:
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


class TestBrandInfoFormatting:
    """브랜드 정보 포맷팅 테스트."""

    def test_format_brand_info_includes_brand_name(self):
        """브랜드명이 포맷팅 결과에 포함되는지 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand_info = {
            "brand_name": "다이트한의원 서울점",
            "summary": "한방 다이어트 전문",
            "extracted_strengths": ["11만 건 처방 경험", "체질별 맞춤 치료"],
            "extracted_services": ["한약 처방", "침 치료"],
        }

        result = _format_brand_info(brand_info)

        # 브랜드명이 가장 먼저 포함되어야 함
        assert "**브랜드명**: 다이트한의원 서울점" in result
        # 브랜드명이 다른 정보보다 먼저 나와야 함
        brand_name_pos = result.find("브랜드명")
        summary_pos = result.find("브랜드 요약")
        assert brand_name_pos < summary_pos

    def test_format_brand_info_without_brand_name(self):
        """브랜드명 없이도 정상 작동하는지 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand_info = {
            "summary": "한방 다이어트 전문",
            "extracted_strengths": ["11만 건 처방 경험"],
        }

        result = _format_brand_info(brand_info)

        # 브랜드명 필드가 없어도 에러 없이 동작
        assert "브랜드 요약" in result
        assert "브랜드명" not in result

    def test_format_brand_info_empty(self):
        """빈 브랜드 정보 처리 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        result = _format_brand_info({})

        assert result == "브랜드 정보 없음"

    def test_build_prompt_includes_brand_info(self):
        """build_prompt에서 브랜드 정보가 프롬프트에 포함되는지 테스트."""
        from src.generator.prompt_builder import build_prompt

        pattern_data = {
            "avg_char_count": 2000,
            "avg_image_count": 5,
            "brand_info": {
                "brand_name": "테스트 브랜드",
                "summary": "테스트 요약",
                "extracted_strengths": ["강점1", "강점2"],
            },
        }

        result = build_prompt(keyword="테스트", pattern_data=pattern_data)

        # 브랜드명이 user 프롬프트에 포함되어야 함
        assert "테스트 브랜드" in result["user"]
        assert "브랜드명" in result["user"]

    def test_pattern_injection_includes_brand_guidelines(self):
        """프롬프트 템플릿에 브랜드 통합 지침이 포함되어 있는지 테스트."""
        from src.generator.prompt_builder import build_prompt

        result = build_prompt(keyword="테스트")

        # 작성 지침 13번이 포함되어야 함
        assert "브랜드 통합" in result["user"]
        assert "4~5회" in result["user"]

    def test_format_brand_info_with_new_fields(self):
        """새로 추가된 브랜드 필드(programs, location, stats)가 포맷팅되는지 테스트."""
        from src.generator.prompt_builder import _format_brand_info

        brand_info = {
            "brand_name": "다이트한의원 서울점",
            "summary": "한방 다이어트 전문",
            "programs": ["다잇단", "BB주사", "맞춤한약"],
            "stats": ["114,948명 치료 경험", "만족도 98%"],
            "location": {
                "address": "서울시 강남구 압구정동 123",
                "nearby_station": "압구정역 3번출구",
                "landmarks": "갤러리아백화점, 현대아파트",
            },
            "team": ["홍길동 원장 (한의학박사)"],
        }

        result = _format_brand_info(brand_info)

        # 프로그램명 포함 확인
        assert "대표 프로그램/제품명" in result
        assert "다잇단" in result
        assert "BB주사" in result

        # 실적/통계 포함 확인
        assert "실적/통계" in result
        assert "114,948명" in result

        # 위치 정보 포함 확인
        assert "위치 정보" in result
        assert "압구정역" in result
        assert "갤러리아백화점" in result

        # 의료진 포함 확인
        assert "전문가/의료진" in result
        assert "홍길동" in result


class TestInsertImagesIntoHtml:
    """_insert_images_into_html 함수 테스트."""

    def test_insert_images_between_paragraphs(self):
        """이미지가 단락 사이에 삽입되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장1</p><p>문장2</p><h2>제목</h2><p>문장3</p>"
        images = [{"filename": "test.jpg", "prompt": "test"}]

        result = _insert_images_into_html(body, images)

        # h2 직전에 이미지가 삽입되어야 함
        assert '<div class="se-image">' in result
        # 이미지 태그 존재 확인 (속성 순서는 BeautifulSoup에 의해 결정됨)
        assert 'src="../images/test.jpg"' in result
        # 문장 중간에 삽입되지 않아야 함 (p 태그 안에 이미지가 없어야 함)
        assert "<p>문장1<div" not in result
        assert "<p>문장2<div" not in result
        assert "<p>문장3<div" not in result

    def test_insert_images_not_in_middle_of_sentence(self):
        """이미지가 문장 중간에 삽입되지 않는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>이것은 긴 문장입니다. 더 많은 내용이 있습니다.</p><h2>제목</h2>"
        images = [{"filename": "test.jpg", "prompt": "test"}]

        result = _insert_images_into_html(body, images)

        # p 태그 안에 이미지가 삽입되지 않아야 함
        assert "<p>이것은 긴 문장입니다. 더 많은 내용이 있습니다.</p>" in result

    def test_insert_multiple_images_distributed(self):
        """여러 이미지가 균등 분산되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장1</p><h2>제목1</h2><p>문장2</p><p>문장3</p><h2>제목2</h2><p>문장4</p>"
        images = [
            {"filename": "1.jpg", "prompt": "img1"},
            {"filename": "2.jpg", "prompt": "img2"},
            {"filename": "3.jpg", "prompt": "img3"},
        ]

        result = _insert_images_into_html(body, images)

        # 3개 이미지가 모두 삽입되어야 함
        assert result.count("se-image") == 3
        # 각 이미지가 존재해야 함
        assert "1.jpg" in result
        assert "2.jpg" in result
        assert "3.jpg" in result

    def test_insert_images_empty_list(self):
        """이미지 리스트가 비어있으면 원본 HTML이 반환되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장1</p><h2>제목</h2>"
        images = []

        result = _insert_images_into_html(body, images)

        assert result == body

    def test_insert_images_no_block_elements(self):
        """블록 요소가 없으면 맨 뒤에 추가되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "단순 텍스트"
        images = [{"filename": "test.jpg", "prompt": "test"}]

        result = _insert_images_into_html(body, images)

        # 이미지가 추가되어야 함
        assert "se-image" in result
        assert "test.jpg" in result

    def test_insert_images_no_h2_uses_p_tags(self):
        """h2가 없으면 p 태그 사이에 삽입되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장1</p><p>문장2</p><p>문장3</p>"
        images = [{"filename": "test.jpg", "prompt": "test"}]

        result = _insert_images_into_html(body, images)

        # 이미지가 삽입되어야 함
        assert "se-image" in result
        # p 태그 안에 삽입되지 않아야 함
        assert "<p>문장<div" not in result

    def test_insert_images_more_than_h2_count(self):
        """이미지가 h2보다 많을 때 p 태그에 분산되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장1</p><h2>제목1</h2><p>문장2</p><p>문장3</p><p>문장4</p>"
        images = [
            {"filename": "1.jpg", "prompt": "img1"},
            {"filename": "2.jpg", "prompt": "img2"},
            {"filename": "3.jpg", "prompt": "img3"},
        ]

        result = _insert_images_into_html(body, images)

        # 3개 이미지가 모두 삽입되어야 함
        assert result.count("se-image") == 3

    def test_insert_images_preserves_html_structure(self):
        """HTML 구조가 유지되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<div><p>내용</p></div><h2>제목</h2><ul><li>항목1</li></ul>"
        images = [{"filename": "test.jpg", "prompt": "test"}]

        result = _insert_images_into_html(body, images)

        # 기존 HTML 구조가 유지되어야 함
        assert "<ul>" in result
        assert "<li>항목1</li>" in result
        assert "</ul>" in result

    def test_insert_images_alt_text_escaped(self):
        """alt 텍스트의 특수문자가 이스케이프되는지 테스트."""
        from src.generator import _insert_images_into_html

        body = "<p>문장</p><h2>제목</h2>"
        images = [{"filename": "test.jpg", "prompt": 'Test "with" <special> chars'}]

        result = _insert_images_into_html(body, images)

        # < > 특수문자가 이스케이프되어야 함
        assert '&lt;special&gt;' in result
        # 이미지 태그가 정상적으로 삽입되어야 함
        assert 'test.jpg' in result