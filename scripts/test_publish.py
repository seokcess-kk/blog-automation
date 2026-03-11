"""
테스트용 발행 스크립트 - 스케줄 제한 우회
"""
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import BLOG_ACCOUNTS
from src.publisher.auth import login_to_naver
from src.publisher.editor import BlogEditor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_publish(blog_account: str = "A"):
    """테스트 발행 실행"""

    account = BLOG_ACCOUNTS.get(blog_account)
    if not account:
        print(f"계정을 찾을 수 없습니다: {blog_account}")
        return

    blog_id = account["blog_id"]
    authenticator = None

    try:
        # 1. 로그인
        print(f"\n=== 로그인 시도: {account['username']} ===")
        authenticator = login_to_naver(
            username=account["username"],
            password=account["password"],
            blog_id=blog_id,
            account=blog_account,
        )
        print("로그인 성공!")

        # 2. 에디터 테스트
        print("\n=== 에디터 테스트 ===")
        page = authenticator.get_page()
        editor = BlogEditor(page, blog_id)

        # 간단한 테스트 글
        test_title = "테스트 글 - 삭제 예정"
        test_body = """
<p>이 글은 자동화 테스트용입니다.</p>
<p>발행 확인 후 삭제하시면 됩니다.</p>
<p>테스트 시간: 2026-03-11</p>
"""
        test_tags = ["테스트", "자동화"]

        print(f"제목: {test_title}")
        print(f"태그: {test_tags}")

        # 3. 글 작성 및 발행
        result = editor.write_and_publish(
            title=test_title,
            body_html=test_body,
            tags=test_tags,
            images=[],
            publish=True,
        )

        print("\n=== 발행 결과 ===")
        print(f"성공: {result['success']}")
        print(f"URL: {result['url']}")
        if result['error']:
            print(f"오류: {result['error']}")
        if result['screenshot']:
            print(f"스크린샷: {result['screenshot']}")

        return result

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if authenticator:
            # --wait 플래그가 있으면 브라우저 유지 (디버깅용)
            if "--wait" in sys.argv:
                input("\n브라우저를 확인하세요. Enter를 누르면 종료합니다...")
            authenticator.close()


if __name__ == "__main__":
    account = sys.argv[1] if len(sys.argv) > 1 else "A"
    test_publish(account)
