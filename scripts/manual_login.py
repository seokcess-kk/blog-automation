"""
네이버 수동 로그인 스크립트.

브라우저를 열어 수동 로그인 후 세션을 저장합니다.
CAPTCHA 발생 시 이 스크립트를 사용하여 세션을 초기화합니다.

사용법:
    python scripts/manual_login.py          # 계정 A 로그인
    python scripts/manual_login.py --account B  # 계정 B 로그인
    python scripts/manual_login.py --verify     # 세션 유효성 검증
"""

import argparse
import sys
import time
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from playwright.sync_api import sync_playwright


def get_user_data_dir(account: str) -> Path:
    """계정별 세션 디렉토리를 반환합니다."""
    base_dir = project_root / "browser_data"
    account_dir = base_dir / f"account_{account}"
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def manual_login(account: str, timeout_seconds: int = 120) -> bool:
    """
    수동 로그인을 수행합니다.

    Args:
        account: 계정 식별자 (A 또는 B)
        timeout_seconds: 로그인 대기 시간 (초)

    Returns:
        로그인 성공 여부
    """
    user_data_dir = get_user_data_dir(account)

    print(f"\n{'='*50}")
    print(f"  네이버 수동 로그인 - 계정 {account}")
    print(f"{'='*50}")
    print(f"\n세션 저장 경로: {user_data_dir}")
    print(f"대기 시간: {timeout_seconds}초")
    print("\n[안내]")
    print("1. 브라우저 창에서 네이버에 로그인해주세요")
    print("2. CAPTCHA가 있으면 해결해주세요")
    print("3. '로그인 상태 유지'를 체크해주세요")
    print("4. 로그인 완료 후 자동으로 세션이 저장됩니다")
    print(f"\n브라우저를 여는 중...")

    with sync_playwright() as p:
        # persistent context로 세션 유지
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )

        page = browser.new_page()

        # 네이버 로그인 페이지로 이동
        page.goto("https://nid.naver.com/nidlogin.login")

        print(f"\n로그인을 완료해주세요... (최대 {timeout_seconds}초 대기)")

        # 로그인 완료 대기 (URL 변경 또는 타임아웃)
        start_time = time.time()
        logged_in = False

        while time.time() - start_time < timeout_seconds:
            current_url = page.url

            # 로그인 성공 확인 (로그인 페이지가 아닌 경우)
            if "nidlogin" not in current_url and "naver.com" in current_url:
                logged_in = True
                break

            # 메인 페이지로 리다이렉트된 경우
            if current_url in ["https://www.naver.com/", "https://naver.com/"]:
                logged_in = True
                break

            remaining = int(timeout_seconds - (time.time() - start_time))
            if remaining % 10 == 0 and remaining > 0:
                print(f"  {remaining}초 남음...")

            time.sleep(1)

        if logged_in:
            print(f"\n로그인 성공!")
            print(f"현재 URL: {page.url}")

            # 세션 저장을 위해 잠시 대기
            time.sleep(2)

            # 네이버 메인으로 이동하여 세션 확인
            page.goto("https://www.naver.com/")
            time.sleep(2)

            # 로그인 상태 확인
            try:
                # 로그인 버튼이 없으면 로그인 상태
                login_btn = page.locator("a.link_login")
                if login_btn.count() == 0:
                    print("세션 저장 완료!")
                else:
                    print("경고: 로그인 상태가 유지되지 않았습니다.")
                    logged_in = False
            except Exception:
                pass
        else:
            print(f"\n타임아웃: {timeout_seconds}초 내에 로그인이 완료되지 않았습니다.")

        browser.close()

    return logged_in


def verify_session(account: str) -> bool:
    """
    저장된 세션의 유효성을 검증합니다.

    Args:
        account: 계정 식별자 (A 또는 B)

    Returns:
        세션 유효 여부
    """
    user_data_dir = get_user_data_dir(account)

    if not user_data_dir.exists():
        print(f"세션 디렉토리가 없습니다: {user_data_dir}")
        return False

    print(f"\n세션 검증 중... (계정 {account})")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=True,  # 검증은 headless로
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
        )

        page = browser.new_page()

        # 네이버 메인 페이지로 이동
        page.goto("https://www.naver.com/")
        time.sleep(2)

        # 로그인 상태 확인
        is_valid = False
        try:
            # 로그인 버튼이 없으면 로그인 상태
            login_btn = page.locator("a.link_login")
            if login_btn.count() == 0:
                is_valid = True
                print(f"세션 유효: 계정 {account} 로그인 상태 확인됨")
            else:
                print(f"세션 만료: 계정 {account} 재로그인 필요")
        except Exception as e:
            print(f"세션 검증 오류: {e}")

        browser.close()

    return is_valid


def verify_all_sessions() -> dict:
    """
    모든 계정의 세션을 검증합니다.

    Returns:
        계정별 세션 상태 딕셔너리
    """
    results = {}

    for account in ["A", "B"]:
        user_data_dir = get_user_data_dir(account)
        if user_data_dir.exists() and any(user_data_dir.iterdir()):
            results[account] = verify_session(account)
        else:
            results[account] = None  # 세션 없음
            print(f"계정 {account}: 세션 없음 (로그인 필요)")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="네이버 수동 로그인 및 세션 관리"
    )
    parser.add_argument(
        "--account", "-a",
        default="A",
        choices=["A", "B"],
        help="로그인할 계정 (기본값: A)"
    )
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        help="세션 유효성 검증만 수행"
    )
    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="모든 계정 세션 검증"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=120,
        help="로그인 대기 시간 (초, 기본값: 120)"
    )

    args = parser.parse_args()

    if args.verify_all:
        results = verify_all_sessions()
        print("\n=== 세션 상태 요약 ===")
        for account, status in results.items():
            if status is None:
                print(f"계정 {account}: 세션 없음")
            elif status:
                print(f"계정 {account}: 유효")
            else:
                print(f"계정 {account}: 만료 (재로그인 필요)")
        return

    if args.verify:
        is_valid = verify_session(args.account)
        sys.exit(0 if is_valid else 1)

    # 수동 로그인 수행
    success = manual_login(args.account, args.timeout)

    if success:
        print(f"\n계정 {args.account} 로그인 및 세션 저장 완료!")
        print(f"세션 경로: {get_user_data_dir(args.account)}")
    else:
        print(f"\n로그인 실패. 다시 시도해주세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
