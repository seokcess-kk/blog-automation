"""
scheduler.py - 발행 스케줄링 모듈

기능:
- generate_publish_time: 발행 시간 생성 (정각/30분 패턴 회피)
- check_daily_limit: 일일 발행 한도 확인
- get_min_interval_ok: 최소 발행 간격 확인
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def generate_publish_time(
    base_hour_range: Tuple[int, int] = None,
    jitter_minutes: int = 15
) -> datetime:
    """
    발행 시간을 생성합니다.
    정각/30분 패턴을 회피하여 자연스러운 시간을 선택합니다.

    Args:
        base_hour_range: 발행 시간대 범위 (시작시, 종료시)
        jitter_minutes: 분 단위 변동폭

    Returns:
        발행 예정 datetime
    """
    from src.config import PUBLISH_HOUR_RANGE

    if base_hour_range is None:
        base_hour_range = PUBLISH_HOUR_RANGE

    now = datetime.now()

    # 시간 선택 (범위 내 랜덤, 종료시 미포함)
    hour = random.randint(base_hour_range[0], base_hour_range[1] - 1)

    # 분 선택 (정각/30분 회피)
    # 00-05, 25-35, 55-00 회피
    avoid_ranges = [(0, 5), (25, 35), (55, 60)]

    while True:
        minute = random.randint(0, 59)
        is_avoided = any(start <= minute <= end for start, end in avoid_ranges)
        if not is_avoided:
            break

    # jitter 적용
    jitter = random.randint(-jitter_minutes, jitter_minutes)
    minute = max(0, min(59, minute + jitter))

    # 오늘 또는 내일 날짜 결정
    target_date = now.date()

    # 이미 지난 시간이면 내일로
    if hour < now.hour or (hour == now.hour and minute <= now.minute):
        target_date = target_date + timedelta(days=1)

    publish_time = datetime.combine(
        target_date,
        datetime.min.time().replace(hour=hour, minute=minute)
    )

    # 초 단위 랜덤화
    seconds = random.randint(0, 59)
    publish_time = publish_time.replace(second=seconds)

    logger.info(f"발행 시간 생성: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}")

    return publish_time


def check_daily_limit(blog_id: str) -> bool:
    """
    일일 발행 한도를 확인합니다.

    Args:
        blog_id: 블로그 ID

    Returns:
        발행 가능 여부 (True: 가능, False: 한도 초과)
    """
    from src.config import PUBLISH_MODES, PUBLISH_MODE

    mode_config = PUBLISH_MODES.get(PUBLISH_MODE, PUBLISH_MODES["conservative"])
    daily_limit = mode_config["daily_limit"]

    # 오늘 발행 건수 조회 (Supabase)
    today_count = _get_today_publish_count(blog_id)

    if today_count >= daily_limit:
        logger.warning(
            f"일일 발행 한도 초과: {blog_id} ({today_count}/{daily_limit})"
        )
        return False

    logger.info(f"일일 발행 가능: {blog_id} ({today_count}/{daily_limit})")
    return True


def get_min_interval_ok(blog_id: str) -> bool:
    """
    최소 발행 간격을 확인합니다.

    Args:
        blog_id: 블로그 ID

    Returns:
        발행 가능 여부 (True: 간격 충족, False: 간격 부족)
    """
    from src.config import PUBLISH_MODES, PUBLISH_MODE

    mode_config = PUBLISH_MODES.get(PUBLISH_MODE, PUBLISH_MODES["conservative"])
    min_interval_hours = mode_config["min_interval_hours"]

    # 마지막 발행 시각 조회
    last_publish_time = _get_last_publish_time(blog_id)

    if last_publish_time is None:
        logger.info(f"첫 발행: {blog_id}")
        return True

    now = datetime.now()
    elapsed = now - last_publish_time
    elapsed_hours = elapsed.total_seconds() / 3600

    if elapsed_hours < min_interval_hours:
        remaining = min_interval_hours - elapsed_hours
        logger.warning(
            f"발행 간격 부족: {blog_id} "
            f"(경과: {elapsed_hours:.1f}시간, 필요: {min_interval_hours}시간, "
            f"남은 시간: {remaining:.1f}시간)"
        )
        return False

    logger.info(
        f"발행 간격 충족: {blog_id} "
        f"(경과: {elapsed_hours:.1f}시간, 필요: {min_interval_hours}시간)"
    )
    return True


def is_weekend_allowed() -> bool:
    """
    주말 발행 허용 여부를 확인합니다.

    Returns:
        주말 발행 가능 여부
    """
    from src.config import PUBLISH_MODES, PUBLISH_MODE

    mode_config = PUBLISH_MODES.get(PUBLISH_MODE, PUBLISH_MODES["conservative"])
    weekend_allowed = mode_config["weekend"]

    now = datetime.now()
    is_weekend = now.weekday() >= 5  # 토(5), 일(6)

    if is_weekend and not weekend_allowed:
        logger.warning(f"주말 발행 비허용 모드: {PUBLISH_MODE}")
        return False

    return True


def can_publish_now(blog_id: str) -> Tuple[bool, str]:
    """
    현재 발행 가능 여부를 종합적으로 확인합니다.

    Args:
        blog_id: 블로그 ID

    Returns:
        (가능 여부, 사유 메시지)
    """
    # 1. 주말 확인
    if not is_weekend_allowed():
        return False, "주말 발행 비허용 모드"

    # 2. 시간대 확인
    from src.config import PUBLISH_HOUR_RANGE

    now = datetime.now()
    if not (PUBLISH_HOUR_RANGE[0] <= now.hour <= PUBLISH_HOUR_RANGE[1]):
        return False, f"발행 시간대 외 ({PUBLISH_HOUR_RANGE[0]}~{PUBLISH_HOUR_RANGE[1]}시)"

    # 3. 일일 한도 확인
    if not check_daily_limit(blog_id):
        return False, "일일 발행 한도 초과"

    # 4. 발행 간격 확인
    if not get_min_interval_ok(blog_id):
        return False, "최소 발행 간격 미충족"

    return True, "발행 가능"


def get_next_available_time(blog_id: str) -> datetime:
    """
    다음 발행 가능 시간을 계산합니다.

    Args:
        blog_id: 블로그 ID

    Returns:
        다음 발행 가능 datetime
    """
    from src.config import PUBLISH_MODES, PUBLISH_MODE, PUBLISH_HOUR_RANGE

    mode_config = PUBLISH_MODES.get(PUBLISH_MODE, PUBLISH_MODES["conservative"])
    min_interval_hours = mode_config["min_interval_hours"]

    now = datetime.now()

    # 마지막 발행 시각 기준 최소 간격 적용
    last_publish_time = _get_last_publish_time(blog_id)

    if last_publish_time:
        next_by_interval = last_publish_time + timedelta(hours=min_interval_hours)
    else:
        next_by_interval = now

    # 발행 시간대 확인
    candidate = max(now, next_by_interval)

    # 시간대 외면 다음 날 시작 시간으로
    if candidate.hour > PUBLISH_HOUR_RANGE[1]:
        candidate = candidate.replace(
            hour=PUBLISH_HOUR_RANGE[0],
            minute=random.randint(5, 25)
        ) + timedelta(days=1)
    elif candidate.hour < PUBLISH_HOUR_RANGE[0]:
        candidate = candidate.replace(
            hour=PUBLISH_HOUR_RANGE[0],
            minute=random.randint(5, 25)
        )

    # 주말 체크
    if not mode_config["weekend"]:
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

    # 정각/30분 회피
    minute = candidate.minute
    if minute in range(0, 6) or minute in range(25, 36) or minute in range(55, 60):
        candidate = candidate.replace(minute=random.randint(6, 24))

    return candidate


def _get_today_publish_count(blog_id: str) -> int:
    """
    오늘 발행 건수를 조회합니다 (Supabase).

    Args:
        blog_id: 블로그 ID

    Returns:
        오늘 발행 건수
    """
    from src.config import SUPABASE_URL, SUPABASE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음. 기본값 0 반환")
        return 0

    try:
        import requests

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_iso = today_start.isoformat()

        url = f"{SUPABASE_URL}/rest/v1/publish_logs"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        params = {
            "blog_id": f"eq.{blog_id}",
            "status": "eq.success",
            "created_at": f"gte.{today_iso}",
            "select": "id",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return len(response.json())

        logger.warning(f"Supabase 조회 실패: {response.status_code}")
        return 0

    except Exception as e:
        logger.error(f"발행 건수 조회 오류: {e}")
        return 0


def _get_last_publish_time(blog_id: str) -> Optional[datetime]:
    """
    마지막 발행 시각을 조회합니다 (Supabase).

    Args:
        blog_id: 블로그 ID

    Returns:
        마지막 발행 datetime 또는 None
    """
    from src.config import SUPABASE_URL, SUPABASE_KEY

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase 설정 없음. None 반환")
        return None

    try:
        import requests

        url = f"{SUPABASE_URL}/rest/v1/publish_logs"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        params = {
            "blog_id": f"eq.{blog_id}",
            "status": "eq.success",
            "select": "created_at",
            "order": "created_at.desc",
            "limit": 1,
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data:
                return datetime.fromisoformat(
                    data[0]["created_at"].replace("Z", "+00:00")
                ).replace(tzinfo=None)

        return None

    except Exception as e:
        logger.error(f"마지막 발행 시각 조회 오류: {e}")
        return None
