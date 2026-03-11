"""
blog-automation 설정 모듈.

환경변수에서 설정값을 로드합니다.
"""

import os
from pathlib import Path
from typing import TypedDict

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# API Keys
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")
NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")

# Supabase
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# 블로그 계정
BLOG_A_USERNAME: str = os.getenv("BLOG_A_USERNAME", "")
BLOG_A_PASSWORD: str = os.getenv("BLOG_A_PASSWORD", "")
BLOG_B_USERNAME: str = os.getenv("BLOG_B_USERNAME", "")
BLOG_B_PASSWORD: str = os.getenv("BLOG_B_PASSWORD", "")

# Slack
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")


class PublishModeConfig(TypedDict):
    """발행 모드 설정 타입."""
    daily_limit: int
    min_interval_hours: int
    weekend: bool


# 발행 모드 설정
PUBLISH_MODES: dict[str, PublishModeConfig] = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal": {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive": {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}

PUBLISH_MODE: str = os.getenv("PUBLISH_MODE", "conservative")
PUBLISH_HOUR_RANGE: tuple[int, int] = (9, 18)

# 타이핑 설정
TYPING_DELAY_MS: tuple[int, int] = (50, 200)
TYPO_PROBABILITY: float = 0.02
MAX_RETRY_COUNT: int = 3

# Claude API 설정
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS: int = 4096
CLAUDE_TEMPERATURE: float = 0.7

# Nano Banana Pro 설정
GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image-preview"

# 출력 디렉토리
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"

# 브라우저 설정
BROWSER_VIEWPORT: dict[str, int] = {"width": 1920, "height": 1080}
BROWSER_LOCALE: str = "ko-KR"
BROWSER_TIMEZONE: str = "Asia/Seoul"
USER_DATA_DIR = PROJECT_ROOT / "browser_data"

# 네이버 블로그 설정
NAVER_BLOG_WRITE_URL: str = "https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}"
STEP_TIMEOUT_SECONDS: int = 30

# headless 모드 (기본값: False - 봇 탐지 우회를 위해)
HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
