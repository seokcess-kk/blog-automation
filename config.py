"""
config.py - 블로그 자동화 시스템 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 블로그 계정 정보
BLOG_ACCOUNTS = {
    "A": {
        "username": os.getenv("BLOG_A_USERNAME", ""),
        "password": os.getenv("BLOG_A_PASSWORD", ""),
        "blog_id": os.getenv("BLOG_A_ID", ""),
    },
    "B": {
        "username": os.getenv("BLOG_B_USERNAME", ""),
        "password": os.getenv("BLOG_B_PASSWORD", ""),
        "blog_id": os.getenv("BLOG_B_ID", ""),
    },
}

# Slack 알림
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# 발행 모드 설정 (SPEC 섹션 6)
PUBLISH_MODES = {
    "conservative": {"daily_limit": 2, "min_interval_hours": 4, "weekend": False},
    "normal": {"daily_limit": 4, "min_interval_hours": 3, "weekend": True},
    "aggressive": {"daily_limit": 5, "min_interval_hours": 2, "weekend": True},
}
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "conservative")
PUBLISH_HOUR_RANGE = (9, 18)

# 스텔스 타이핑 설정
TYPING_DELAY_MS = (50, 200)
TYPO_PROBABILITY = 0.02

# 재시도 설정
MAX_RETRY_COUNT = 3
STEP_TIMEOUT_SECONDS = 30

# 브라우저 설정
BROWSER_VIEWPORT = {"width": 1920, "height": 1080}
BROWSER_LOCALE = "ko-KR"
BROWSER_TIMEZONE = "Asia/Seoul"
USER_DATA_DIR = PROJECT_ROOT / "browser_data"

# 네이버 URL
NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
NAVER_BLOG_WRITE_URL = "https://blog.naver.com/{blog_id}/postwrite"
