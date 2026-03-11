"""
HTML 프리뷰 내보내기.

생성된 원고를 브라우저에서 열어 복사 → 네이버 SE ONE 에디터에 붙여넣기할 수 있는
HTML 파일로 출력합니다.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from src.config import HTML_DIR

logger = logging.getLogger(__name__)

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      max-width: 750px;
      margin: 0 auto;
      padding: 24px;
      font-family: '나눔고딕', 'Nanum Gothic', sans-serif;
      font-size: 16px;
      line-height: 1.8;
      color: #333;
    }}
    h1 {{
      font-size: 1.6em;
      margin-bottom: 24px;
    }}
    h2 {{
      font-size: 1.3em;
      border-bottom: 2px solid #00c73c;
      padding-bottom: 8px;
      margin-top: 32px;
    }}
    h3 {{
      font-size: 1.1em;
      margin-top: 24px;
    }}
    p {{
      margin: 12px 0;
    }}
    img {{
      max-width: 100%;
      margin: 16px 0;
      border-radius: 4px;
    }}
    .copy-guide {{
      background: #f5f5f5;
      padding: 16px;
      margin-bottom: 24px;
      border-radius: 8px;
      border-left: 4px solid #00c73c;
      font-size: 14px;
    }}
    .copy-guide strong {{
      color: #00c73c;
    }}
    .tags {{
      color: #00c73c;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #eee;
      font-size: 14px;
    }}
    .meta {{
      color: #999;
      font-size: 12px;
      margin-top: 16px;
      padding-top: 8px;
      border-top: 1px solid #eee;
    }}
    #content {{
      /* 복사 영역 */
    }}
  </style>
</head>
<body>
  <div class="copy-guide">
    <strong>사용법:</strong> 아래 내용을 드래그 &rarr; 복사(Ctrl+C) &rarr; 네이버 블로그 에디터에 붙여넣기(Ctrl+V)<br>
    이미지는 <code>images/</code> 폴더에서 에디터로 수동 업로드하세요.
  </div>

  <div id="content">
    <h1>{title}</h1>
{body_with_images}
  </div>

  <div class="tags">
    {tags_html}
  </div>

  <div class="meta">
    키워드: {keyword} | 생성일: {created_at}
  </div>
</body>
</html>
"""


def export_to_html(
    title: str,
    body_html: str,
    tags: list[str],
    images: list[dict] | None = None,
    keyword: str = "",
    output_path: Path | None = None,
) -> Path:
    """
    원고를 HTML 프리뷰 파일로 내보냅니다.

    Args:
        title: 블로그 제목
        body_html: 본문 HTML
        tags: 태그 목록
        images: 이미지 정보 리스트 [{path, prompt, filename}]
        keyword: 타겟 키워드
        output_path: 출력 경로 (None이면 자동 생성)

    Returns:
        생성된 HTML 파일 경로
    """
    if images is None:
        images = []

    # 위험 태그 제거 (XSS 방지)
    body_html = _strip_dangerous_tags(body_html)

    # 이미지를 본문 섹션 사이에 배치
    body_with_images = _insert_images_between_sections(body_html, images)

    # 태그 HTML
    tags_html = " ".join(f"#{tag}" for tag in tags) if tags else ""

    # 생성일
    now = datetime.now()
    created_at = now.strftime("%Y-%m-%d %H:%M")

    # HTML 렌더링
    html = _HTML_TEMPLATE.format(
        title=_escape_html(title),
        body_with_images=body_with_images,
        tags_html=_escape_html(tags_html),
        keyword=_escape_html(keyword),
        created_at=created_at,
    )

    # 출력 경로 결정
    if output_path is None:
        HTML_DIR.mkdir(parents=True, exist_ok=True)
        safe_keyword = re.sub(r'[^\w가-힣]', '_', keyword or "draft")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        output_path = HTML_DIR / f"{safe_keyword}_{timestamp}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    logger.info(f"HTML 프리뷰 생성 완료: {output_path}")
    return output_path


def _insert_images_between_sections(body_html: str, images: list[dict]) -> str:
    """본문 HTML의 <h2> 섹션 사이에 이미지를 순차 배치합니다."""
    if not images:
        return body_html

    # <h2> 기준으로 섹션 분할
    parts = re.split(r'(?=<h2[\s>])', body_html)

    if len(parts) <= 1:
        # h2가 없으면 본문 끝에 이미지 추가
        img_tags = _build_image_tags(images)
        return body_html + "\n" + img_tags

    # 각 섹션 뒤에 이미지 1~2개씩 배치
    result_parts = []
    img_idx = 0
    images_per_section = max(1, len(images) // max(len(parts) - 1, 1))

    for i, part in enumerate(parts):
        result_parts.append(part)
        # 첫 번째 파트(h2 이전 내용)는 건너뜀
        if i > 0 and img_idx < len(images):
            count = min(images_per_section, len(images) - img_idx, 2)
            section_images = images[img_idx:img_idx + count]
            result_parts.append(_build_image_tags(section_images))
            img_idx += count

    # 남은 이미지는 마지막에 추가
    if img_idx < len(images):
        result_parts.append(_build_image_tags(images[img_idx:]))

    return "\n".join(result_parts)


def _build_image_tags(images: list[dict]) -> str:
    """이미지 딕셔너리 리스트에서 <img> 태그를 생성합니다."""
    tags = []
    for img in images:
        path = img.get("path", "")
        filename = img.get("filename", "")
        alt = img.get("alt", img.get("prompt", ""))

        # 상대 경로 사용 (images/ 폴더 기준)
        if path:
            src = f"../images/{Path(path).name}"
        elif filename:
            src = f"../images/{filename}"
        else:
            continue

        tags.append(f'    <img src="{_escape_html(src)}" alt="{_escape_html(alt)}">')

    return "\n".join(tags)


def _strip_dangerous_tags(html: str) -> str:
    """body_html에서 위험한 태그를 제거합니다 (XSS 방지)."""
    # 콘텐츠가 있는 위험 태그 (열기+닫기)
    paired_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<form[^>]*>.*?</form>',
    ]
    for pattern in paired_patterns:
        html = re.compile(pattern, re.IGNORECASE | re.DOTALL).sub('', html)

    # self-closing 위험 태그
    html = re.compile(
        r'<(script|iframe|object|embed)\b[^>]*/?\s*>', re.IGNORECASE
    ).sub('', html)

    # 이벤트 핸들러 속성 제거 (onclick, onerror 등 - 실제 DOM 이벤트만)
    html = re.compile(
        r'\bon(click|dblclick|mouse\w+|key\w+|focus|blur|change|submit|reset|'
        r'load|unload|error|resize|scroll|select|abort|contextmenu'
        r')\s*=\s*["\'][^"\']*["\']',
        re.IGNORECASE,
    ).sub('', html)

    return html


def _escape_html(text: str) -> str:
    """기본 HTML 이스케이프."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
