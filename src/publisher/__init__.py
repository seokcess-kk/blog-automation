"""
publisher - 네이버 블로그 자동 발행 모듈

주요 기능:
- publish_draft: 드래프트 발행 파이프라인
- auth: 네이버 로그인 (Pyperclip 클립보드 우회)
- editor: 블로그 에디터 자동화
- stealth: 봇 탐지 우회 (human_typing, 핑거프린트 랜덤화)
- scheduler: 발행 스케줄링 (일일 한도, 간격 관리)
"""
import logging
from typing import Optional
from datetime import datetime

from src.publisher.auth import NaverAuthenticator, login_to_naver
from src.publisher.editor import BlogEditor
from src.publisher.stealth import (
    human_delay,
    human_typing,
    random_mouse_movement,
    setup_stealth_browser,
)
from src.publisher.scheduler import (
    generate_publish_time,
    check_daily_limit,
    get_min_interval_ok,
    can_publish_now,
    get_next_available_time,
)

logger = logging.getLogger(__name__)

__all__ = [
    "publish_draft",
    "NaverAuthenticator",
    "login_to_naver",
    "BlogEditor",
    "human_delay",
    "human_typing",
    "random_mouse_movement",
    "setup_stealth_browser",
    "generate_publish_time",
    "check_daily_limit",
    "get_min_interval_ok",
    "can_publish_now",
    "get_next_available_time",
]


def publish_draft(draft_id: str, blog_account: str = "A") -> dict:
    """
    드래프트를 발행합니다.

    전체 파이프라인:
    1. 스케줄 확인 (일일 한도, 발행 간격)
    2. Supabase에서 드래프트 조회
    3. 네이버 로그인 (auth)
    4. 블로그 에디터에서 글 작성 및 발행 (editor)
    5. 발행 결과 로깅

    Args:
        draft_id: 발행할 드래프트의 UUID
        blog_account: 사용할 블로그 계정 ("A" 또는 "B")

    Returns:
        발행 결과 딕셔너리
        {
            "success": bool,
            "draft_id": str,
            "blog_id": str,
            "post_url": str | None,
            "error": str | None,
            "published_at": str | None,
        }
    """
    from src.config import BLOG_ACCOUNTS, SUPABASE_URL, SUPABASE_KEY

    result = {
        "success": False,
        "draft_id": draft_id,
        "blog_id": None,
        "post_url": None,
        "error": None,
        "published_at": None,
    }

    authenticator: Optional[NaverAuthenticator] = None

    try:
        # 1. 계정 정보 확인
        account = BLOG_ACCOUNTS.get(blog_account)
        if not account:
            raise ValueError(f"잘못된 블로그 계정: {blog_account}")

        blog_id = account["blog_id"]
        result["blog_id"] = blog_id

        # 2. 발행 가능 여부 확인
        can_publish, reason = can_publish_now(blog_id)
        if not can_publish:
            result["error"] = f"발행 불가: {reason}"
            logger.warning(result["error"])
            return result

        # 3. Supabase에서 드래프트 조회
        draft = _fetch_draft(draft_id)
        if not draft:
            result["error"] = f"드래프트 조회 실패: {draft_id}"
            logger.error(result["error"])
            return result

        # 4. 네이버 로그인
        logger.info(f"발행 시작: {draft['title'][:30]}...")

        authenticator = login_to_naver(
            username=account["username"],
            password=account["password"],
            blog_id=blog_id,
        )

        # 5. 블로그 에디터에서 글 작성 및 발행
        page = authenticator.get_page()
        editor = BlogEditor(page, blog_id)

        # 이미지 파일 경로 추출
        images = _extract_image_paths(draft.get("images", []))

        editor_result = editor.write_and_publish(
            title=draft["title"],
            body_html=draft["body_html"],
            tags=draft.get("tags", []),
            images=images,
            publish=True,
        )

        if editor_result["success"]:
            result["success"] = True
            result["post_url"] = editor_result["url"]
            result["published_at"] = datetime.now().isoformat()

            # 6. Supabase 업데이트
            _update_draft_status(draft_id, "published", editor_result["url"])
            _log_publish_result(draft_id, blog_id, "publish", "success")

            logger.info(f"발행 완료: {result['post_url']}")
        else:
            result["error"] = editor_result["error"]
            _update_draft_status(draft_id, "failed", error=result["error"])
            _log_publish_result(draft_id, blog_id, "publish", "failed", result["error"])

            logger.error(f"발행 실패: {result['error']}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"발행 오류: {e}")

        # 실패 로깅
        if result["blog_id"]:
            _log_publish_result(
                draft_id, result["blog_id"], "publish", "error", str(e)
            )

    finally:
        # 브라우저 정리
        if authenticator:
            authenticator.close()

    return result


def _fetch_draft(draft_id: str) -> Optional[dict]:
    """
    Supabase에서 드래프트를 조회합니다.

    Args:
        draft_id: 드래프트 UUID

    Returns:
        드래프트 데이터 또는 None
    """
    from config import SUPABASE_URL, SUPABASE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음. 테스트 데이터 반환")
        return {
            "id": draft_id,
            "title": "테스트 제목",
            "body_html": "<p>테스트 본문입니다.</p>",
            "tags": ["테스트"],
            "images": [],
        }

    try:
        import requests

        url = f"{SUPABASE_URL}/rest/v1/drafts"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        params = {
            "id": f"eq.{draft_id}",
            "select": "*",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]

        logger.warning(f"드래프트 조회 실패: {response.status_code}")
        return None

    except Exception as e:
        logger.error(f"드래프트 조회 오류: {e}")
        return None


def _extract_image_paths(images: list) -> list:
    """
    이미지 정보에서 파일 경로를 추출합니다.

    Args:
        images: 이미지 정보 리스트 (JSONB)

    Returns:
        이미지 파일 경로 리스트
    """
    paths = []
    for img in images:
        if isinstance(img, str):
            paths.append(img)
        elif isinstance(img, dict) and "path" in img:
            paths.append(img["path"])
    return paths


def _update_draft_status(
    draft_id: str,
    status: str,
    post_url: str = None,
    error: str = None
) -> None:
    """
    드래프트 상태를 업데이트합니다.

    Args:
        draft_id: 드래프트 UUID
        status: 새 상태
        post_url: 발행된 글 URL
        error: 에러 메시지
    """
    from config import SUPABASE_URL, SUPABASE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음. 상태 업데이트 스킵")
        return

    try:
        import requests

        url = f"{SUPABASE_URL}/rest/v1/drafts"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        params = {"id": f"eq.{draft_id}"}

        data = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }
        if post_url:
            data["naver_post_url"] = post_url
            data["published_at"] = datetime.now().isoformat()
        if error:
            data["error_log"] = error

        response = requests.patch(
            url, headers=headers, params=params, json=data, timeout=10
        )

        if response.status_code in (200, 204):
            logger.info(f"드래프트 상태 업데이트: {status}")
        else:
            logger.warning(f"드래프트 상태 업데이트 실패: {response.status_code}")

    except Exception as e:
        logger.error(f"드래프트 상태 업데이트 오류: {e}")


def _log_publish_result(
    draft_id: str,
    blog_id: str,
    action: str,
    status: str,
    error_detail: str = None
) -> None:
    """
    발행 결과를 로깅합니다.

    Args:
        draft_id: 드래프트 UUID
        blog_id: 블로그 ID
        action: 수행한 액션
        status: 결과 상태
        error_detail: 에러 상세
    """
    from config import SUPABASE_URL, SUPABASE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음. 로깅 스킵")
        return

    try:
        import requests

        url = f"{SUPABASE_URL}/rest/v1/publish_logs"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        data = {
            "draft_id": draft_id,
            "blog_id": blog_id,
            "action": action,
            "status": status,
            "error_detail": error_detail,
            "created_at": datetime.now().isoformat(),
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code in (200, 201):
            logger.debug(f"발행 로그 기록: {action} - {status}")
        else:
            logger.warning(f"발행 로그 기록 실패: {response.status_code}")

    except Exception as e:
        logger.error(f"발행 로그 기록 오류: {e}")
