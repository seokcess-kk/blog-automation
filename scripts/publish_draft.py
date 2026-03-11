"""
실제 드래프트 발행 스크립트 - 스케줄 제한 우회
"""
import sys
import logging
import requests
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import BLOG_ACCOUNTS, SUPABASE_URL, SUPABASE_KEY
from src.publisher.auth import login_to_naver
from src.publisher.editor import BlogEditor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_draft(draft_id: str) -> dict:
    """Supabase에서 드래프트 조회"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음")
        return None

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
    return None


def publish_draft(draft_id: str, blog_account: str = "A"):
    """드래프트 발행"""

    # 1. 드래프트 조회
    print(f"\n=== 드래프트 조회: {draft_id} ===")
    draft = fetch_draft(draft_id)

    if not draft:
        print("드래프트를 찾을 수 없습니다.")
        return

    print(f"제목: {draft['title']}")
    print(f"태그: {draft.get('tags', [])}")
    print(f"본문 길이: {len(draft.get('body_html', ''))} 자")

    # 2. 계정 정보
    account = BLOG_ACCOUNTS.get(blog_account)
    if not account:
        print(f"계정을 찾을 수 없습니다: {blog_account}")
        return

    blog_id = account["blog_id"]
    authenticator = None

    try:
        # 3. 로그인
        print(f"\n=== 로그인: {account['username']} ===")
        authenticator = login_to_naver(
            username=account["username"],
            password=account["password"],
            blog_id=blog_id,
            account=blog_account,
        )
        print("로그인 성공!")

        # 4. 에디터로 발행
        print("\n=== 발행 시작 ===")
        page = authenticator.get_page()
        editor = BlogEditor(page, blog_id)

        # 이미지 경로 추출
        images = []
        for img in draft.get("images", []):
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict) and "path" in img:
                images.append(img["path"])

        result = editor.write_and_publish(
            title=draft["title"],
            body_html=draft.get("body_html", ""),
            tags=draft.get("tags", []),
            images=images,
            publish=True,
        )

        print("\n=== 발행 결과 ===")
        print(f"성공: {result['success']}")
        print(f"URL: {result['url']}")
        if result['error']:
            print(f"오류: {result['error']}")

        # 5. Supabase 업데이트
        if result['success'] and result['url']:
            update_draft_status(draft_id, "published", result['url'])
            print("\n드래프트 상태 업데이트 완료 (published)")

        return result

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if authenticator:
            authenticator.close()


def update_draft_status(draft_id: str, status: str, post_url: str = None):
    """드래프트 상태 업데이트"""
    from datetime import datetime

    if not SUPABASE_URL or not SUPABASE_KEY:
        return

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

    requests.patch(url, headers=headers, params=params, json=data, timeout=10)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish_draft.py <draft_id> [account]")
        print("Example: python publish_draft.py 3ad44da6-9cd2-4fa4-8486-98b5cde40c14 A")
        sys.exit(1)

    draft_id = sys.argv[1]
    account = sys.argv[2] if len(sys.argv) > 2 else "A"

    publish_draft(draft_id, account)
