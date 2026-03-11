"""
exporter 모듈 테스트.

pytest 실행: pytest tests/test_exporter.py -v
"""

import pytest
from pathlib import Path


class TestHtmlExporter:
    """html_exporter 모듈 테스트."""

    def test_export_creates_html_file(self, tmp_path):
        """HTML 파일이 정상적으로 생성되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "test.html"
        result = export_to_html(
            title="테스트 제목",
            body_html="<p>본문 내용입니다.</p>",
            tags=["태그1", "태그2"],
            keyword="테스트",
            output_path=output,
        )

        assert result == output
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "테스트 제목" in content
        assert "본문 내용입니다." in content

    def test_export_contains_tags(self, tmp_path):
        """태그가 HTML에 포함되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "tags.html"
        export_to_html(
            title="제목",
            body_html="<p>본문</p>",
            tags=["SEO", "블로그", "최적화"],
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "#SEO" in content
        assert "#블로그" in content
        assert "#최적화" in content

    def test_export_contains_copy_guide(self, tmp_path):
        """복사 가이드가 HTML에 포함되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "guide.html"
        export_to_html(
            title="제목",
            body_html="<p>본문</p>",
            tags=[],
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "copy-guide" in content
        assert "사용법" in content

    def test_export_auto_generates_path(self):
        """output_path 미지정 시 자동 경로 생성 테스트."""
        from src.exporter.html_exporter import export_to_html

        result = export_to_html(
            title="자동경로 테스트",
            body_html="<p>테스트</p>",
            tags=[],
            keyword="자동경로",
        )

        try:
            assert result.exists()
            assert result.suffix == ".html"
            assert "자동경로" in result.name
            assert "output" in str(result) or "html" in str(result)
        finally:
            # 정리
            result.unlink(missing_ok=True)

    def test_export_with_images(self, tmp_path):
        """이미지가 섹션 사이에 삽입되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        body = "<h2>섹션1</h2><p>내용1</p><h2>섹션2</h2><p>내용2</p>"
        images = [
            {"path": "/images/img1.jpg", "prompt": "이미지1"},
            {"path": "/images/img2.jpg", "prompt": "이미지2"},
        ]

        output = tmp_path / "images.html"
        export_to_html(
            title="이미지 테스트",
            body_html=body,
            tags=[],
            images=images,
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "img1.jpg" in content
        assert "img2.jpg" in content
        assert "<img" in content

    def test_export_no_h2_images_at_end(self, tmp_path):
        """h2가 없으면 이미지가 끝에 추가되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        images = [{"path": "/images/img1.jpg", "prompt": "이미지"}]
        output = tmp_path / "no_h2.html"

        export_to_html(
            title="제목",
            body_html="<p>h2 없는 본문</p>",
            tags=[],
            images=images,
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "img1.jpg" in content

    def test_export_empty_images(self, tmp_path):
        """이미지 없이도 정상 동작하는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "no_images.html"
        export_to_html(
            title="제목",
            body_html="<p>본문</p>",
            tags=["태그"],
            images=[],
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "<img" not in content
        assert "본문" in content

    def test_export_html_escaping(self, tmp_path):
        """HTML 특수문자가 이스케이프되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "escape.html"
        export_to_html(
            title='제목 <script>alert("xss")</script>',
            body_html="<p>본문</p>",
            tags=[],
            keyword='키워드 & "특수"',
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content
        assert "&amp;" in content

    def test_export_keyword_in_meta(self, tmp_path):
        """키워드가 메타 영역에 표시되는지 테스트."""
        from src.exporter.html_exporter import export_to_html

        output = tmp_path / "meta.html"
        export_to_html(
            title="제목",
            body_html="<p>본문</p>",
            tags=[],
            keyword="맛집 추천",
            output_path=output,
        )

        content = output.read_text(encoding="utf-8")
        assert "맛집 추천" in content


class TestImageCounting:
    """이미지 카운팅 개선 테스트."""

    def test_is_icon_image_filters_decorative(self):
        """장식용 이미지가 필터링되는지 테스트."""
        from src.analyzer.content_parser import _is_icon_image

        # 장식용 이미지 (True 반환)
        assert _is_icon_image("https://s.pstatic.net/icon.png") is True
        assert _is_icon_image("https://example.com/separator.png") is True  # /separator 매칭
        assert _is_icon_image("https://example.com/img/separator.png") is True  # /separator 매칭
        assert _is_icon_image("https://example.com/bg_pattern.jpg") is True
        assert _is_icon_image("https://example.com/img/arrow.png") is True  # /arrow 매칭
        assert _is_icon_image("https://example.com/site_logo.png") is True  # _logo 매칭
        assert _is_icon_image("https://example.com/sticker_01.png") is True
        assert _is_icon_image("https://example.com/img/badge.png") is True  # /badge 매칭

        # 콘텐츠 이미지 (False 반환) - 오탐 방지
        assert _is_icon_image("https://blogfiles.naver.net/photo.jpg") is False
        assert _is_icon_image("https://postfiles.naver.net/image.png") is False
        assert _is_icon_image("https://example.com/food_review.jpg") is False
        assert _is_icon_image("https://example.com/checkout_guide.jpg") is False  # check 오탐 방지
        assert _is_icon_image("https://example.com/polkadot_cafe.jpg") is False  # dot 오탐 방지

    def test_is_small_image_filters_by_size(self):
        """크기 기반 필터링 테스트."""
        from src.analyzer.content_parser import _is_small_image
        from unittest.mock import Mock

        # 작은 이미지 (width, height 모두 < 100)
        small_img = Mock()
        small_img.attrib = {"width": "50", "height": "50"}
        assert _is_small_image(small_img) is True

        # 큰 이미지
        large_img = Mock()
        large_img.attrib = {"width": "800", "height": "600"}
        assert _is_small_image(large_img) is False

        # 크기 정보 없는 이미지
        no_size_img = Mock()
        no_size_img.attrib = {}
        assert _is_small_image(no_size_img) is False

        # 배너형 이미지 (width 작고 height 큼) - 필터되면 안 됨
        banner_img = Mock()
        banner_img.attrib = {"width": "50", "height": "800"}
        assert _is_small_image(banner_img) is False

        # 가로 배너 (width 큼, height 작음) - 필터되면 안 됨
        wide_banner = Mock()
        wide_banner.attrib = {"width": "800", "height": "30"}
        assert _is_small_image(wide_banner) is False

        # width만 있는 경우 - 다른 축 모르므로 필터하지 않음
        width_only = Mock()
        width_only.attrib = {"width": "50"}
        assert _is_small_image(width_only) is False

    def test_is_small_image_inline_style(self):
        """inline style에서 크기 파싱 테스트."""
        from src.analyzer.content_parser import _is_small_image
        from unittest.mock import Mock

        # inline style로 작은 크기
        img = Mock()
        img.attrib = {"style": "width: 32px; height: 32px;"}
        assert _is_small_image(img) is True

        # inline style로 큰 크기
        img2 = Mock()
        img2.attrib = {"style": "width: 500px; height: 300px;"}
        assert _is_small_image(img2) is False
