"""
blog-automation CLI 인터페이스.

n8n Execute Command 노드에서 호출하기 위한 CLI 진입점입니다.
모든 명령어는 JSON stdout으로 결과를 반환합니다.

사용법:
    python -m src.cli analyze --keyword "키워드"
    python -m src.cli generate --keyword-id <uuid>
    python -m src.cli publish --draft-id <uuid>
    python -m src.cli check-schedule
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional

import click

from src.config import SUPABASE_URL, SUPABASE_KEY

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def output_json(data: dict[str, Any]) -> None:
    """JSON 결과를 stdout으로 출력합니다."""
    import sys
    sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def output_error(message: str) -> None:
    """에러를 JSON 형식으로 출력하고 종료합니다."""
    output_json({"success": False, "error": message})
    sys.exit(1)


def get_supabase_client():
    """Supabase 클라이언트를 반환합니다."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        import requests
        return {"url": SUPABASE_URL, "key": SUPABASE_KEY}
    except ImportError:
        return None


def supabase_select(table: str, filters: dict) -> Optional[list]:
    """Supabase에서 데이터를 조회합니다."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        import requests

        url = f"{client['url']}/rest/v1/{table}"
        headers = {
            "apikey": client["key"],
            "Authorization": f"Bearer {client['key']}",
        }
        params = {k: f"eq.{v}" for k, v in filters.items()}
        params["select"] = "*"

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None

    except Exception as e:
        logger.error(f"Supabase 조회 오류: {e}")
        return None


def supabase_insert(table: str, data: dict) -> Optional[dict]:
    """Supabase에 데이터를 삽입합니다."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        import requests

        url = f"{client['url']}/rest/v1/{table}"
        headers = {
            "apikey": client["key"],
            "Authorization": f"Bearer {client['key']}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code in (200, 201):
            result = response.json()
            return result[0] if result else None
        return None

    except Exception as e:
        logger.error(f"Supabase 삽입 오류: {e}")
        return None


def supabase_update(table: str, filters: dict, data: dict) -> bool:
    """Supabase 데이터를 업데이트합니다."""
    client = get_supabase_client()
    if not client:
        return False

    try:
        import requests

        url = f"{client['url']}/rest/v1/{table}"
        headers = {
            "apikey": client["key"],
            "Authorization": f"Bearer {client['key']}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        params = {k: f"eq.{v}" for k, v in filters.items()}

        response = requests.patch(
            url, headers=headers, params=params, json=data, timeout=10
        )

        return response.status_code in (200, 204)

    except Exception as e:
        logger.error(f"Supabase 업데이트 오류: {e}")
        return False


@click.group()
def cli():
    """blog-automation CLI - 네이버 블로그 자동화 도구"""
    pass


@cli.command()
@click.option("--keyword", required=True, help="분석할 키워드")
@click.option("--top-n", default=5, help="분석할 상위 블로그 개수")
@click.option("--save-to-db", is_flag=True, help="결과를 DB에 저장")
@click.option("--no-deep", is_flag=True, help="Gemini Flash 심층 분석 비활성화")
@click.option("--brand-url", default=None, help="브랜드 홈페이지 URL")
@click.option("--brand-name", default=None, help="브랜드명")
@click.option("--brand-location", default=None, help="브랜드 위치 정보 (예: '정발산역 인근, 낙원프라자 4층')")
@click.option("--brand-programs", default=None, help="대표 프로그램명 (쉼표 구분, 예: '다잇단,BB주사,맞춤한약')")
def analyze(keyword: str, top_n: int, save_to_db: bool, no_deep: bool, brand_url: Optional[str], brand_name: Optional[str], brand_location: Optional[str], brand_programs: Optional[str]):
    """
    키워드 상위노출 패턴을 분석합니다.

    네이버 검색 상위 블로그들을 분석하여 패턴을 추출합니다.
    --brand-url 옵션을 사용하면 브랜드 홈페이지를 크롤링하여 브랜드 정보를 추출합니다.
    """
    try:
        from src.analyzer import analyze_keyword

        logger.info(f"키워드 분석 시작: '{keyword}'")

        result = analyze_keyword(keyword, top_n=top_n, include_raw_data=False, no_deep=no_deep)

        if not result["success"]:
            output_error(result.get("error", "분석 실패"))

        # 브랜드 크롤링 (옵션)
        brand_info_dict = None
        if brand_url:
            from src.analyzer import crawl_brand_homepage, brand_info_to_dict

            logger.info(f"브랜드 크롤링 시작: {brand_url}")
            brand_info = crawl_brand_homepage(brand_url, brand_name=brand_name)
            if brand_info:
                brand_info_dict = brand_info_to_dict(brand_info)
                # brand_name을 brand_info에 명시적 추가
                if brand_name and "brand_name" not in brand_info_dict:
                    brand_info_dict["brand_name"] = brand_name
                result["brand_info"] = brand_info_dict
                logger.info(f"브랜드 크롤링 완료: 브랜드명={brand_name}, 강점={len(brand_info.extracted_strengths)}")
            else:
                logger.warning("브랜드 크롤링 실패 (계속 진행)")

        # CLI에서 직접 입력한 브랜드 정보 병합 (크롤링 결과보다 우선)
        if brand_info_dict is None and (brand_name or brand_location or brand_programs):
            brand_info_dict = {}

        if brand_info_dict is not None:
            # 위치 정보 (CLI 입력 우선)
            if brand_location:
                brand_info_dict["location"] = {"nearby_station": brand_location}
                logger.info(f"위치 정보 추가: {brand_location}")

            # 프로그램명 (CLI 입력 우선, 기존 값과 병합)
            if brand_programs:
                cli_programs = [p.strip() for p in brand_programs.split(",") if p.strip()]
                existing_programs = brand_info_dict.get("programs", [])
                # CLI 입력을 앞에 배치 (우선순위)
                merged_programs = cli_programs + [p for p in existing_programs if p not in cli_programs]
                brand_info_dict["programs"] = merged_programs[:5]
                logger.info(f"프로그램 추가: {cli_programs}")

            # brand_name 다시 확인
            if brand_name and "brand_name" not in brand_info_dict:
                brand_info_dict["brand_name"] = brand_name

            result["brand_info"] = brand_info_dict

        # DB 저장
        if save_to_db and result["success"]:
            # patterns 테이블에 저장
            raw_data = result["pattern"].copy()
            if brand_info_dict:
                raw_data["brand_info"] = brand_info_dict

            pattern_data = {
                "keyword": keyword,
                "source_urls": result.get("source_urls", []),
                "avg_char_count": result["pattern"].get("avg_char_count"),
                "avg_image_count": result["pattern"].get("avg_image_count"),
                "avg_heading_count": result["pattern"].get("avg_heading_count"),
                "title_patterns": result["pattern"].get("title_patterns"),
                "keyword_placement": result["pattern"].get("keyword_placement"),
                "related_keywords": result["pattern"].get("related_keywords"),
                "content_structure": result["pattern"].get("content_structure"),
                "raw_data": raw_data,
                "analyzed_at": datetime.now().isoformat(),
            }

            inserted = supabase_insert("patterns", pattern_data)
            if inserted:
                result["pattern_id"] = inserted.get("id")
                logger.info(f"패턴 저장 완료: {result['pattern_id']}")
            else:
                logger.warning("패턴 DB 저장 실패 (Supabase 미설정 또는 오류)")

        output_json(result)

    except Exception as e:
        logger.error(f"분석 오류: {e}")
        output_error(str(e))


@cli.command()
@click.option("--keyword-id", required=True, help="키워드 ID (UUID)")
@click.option("--skip-images", is_flag=True, help="이미지 생성 스킵")
@click.option("--output-html/--no-output-html", default=True, help="HTML 프리뷰 출력 (기본: True)")
def generate(keyword_id: str, skip_images: bool, output_html: bool):
    """
    키워드ID로 패턴을 로드하여 원고를 생성합니다.

    패턴 데이터를 기반으로 블로그 콘텐츠와 이미지를 생성합니다.
    생성 완료 후 HTML 프리뷰 파일을 자동 출력합니다.
    """
    try:
        from src.generator import generate_content
        from src.publisher.scheduler import generate_publish_time

        logger.info(f"원고 생성 시작: keyword_id={keyword_id}")

        # 1. 패턴 데이터 로드
        patterns = supabase_select("patterns", {"keyword_id": keyword_id}) or []

        if not patterns:
            # keyword_id로 직접 patterns 조회 시도
            patterns = supabase_select("patterns", {"id": keyword_id}) or []

        pattern_data = patterns[0] if patterns else None
        keyword = pattern_data.get("keyword", keyword_id) if pattern_data else keyword_id

        # raw_data 추출 및 JSON 파싱 안전 처리
        raw_data = pattern_data.get("raw_data") if pattern_data else None
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except json.JSONDecodeError:
                logger.warning("raw_data JSON 파싱 실패, 빈 딕셔너리로 대체")
                raw_data = {}

        # brand_info가 raw_data 내부에 있는 경우 pattern_data로 복사
        if raw_data and isinstance(raw_data, dict):
            if "brand_info" in raw_data and pattern_data is not None and "brand_info" not in pattern_data:
                pattern_data["brand_info"] = raw_data["brand_info"]
            # deep_analysis에서 토픽/경쟁사 정보 추출하여 최상위로
            deep_analysis = raw_data.get("deep_analysis")
            if deep_analysis and isinstance(deep_analysis, dict):
                if "common_topics" not in raw_data:
                    raw_data["common_topics"] = deep_analysis.get("common_topics", [])
                if "filtered_competitors" not in raw_data:
                    raw_data["filtered_competitors"] = deep_analysis.get("filtered_competitors", [])
                if "topic_outline" not in raw_data:
                    raw_data["topic_outline"] = deep_analysis.get("topic_outline", "")

        # 2. 콘텐츠 생성
        content_result = generate_content(
            keyword_id=keyword_id,
            keyword=keyword,
            pattern_data=raw_data,
            skip_images=skip_images,
        )

        # 3. 발행 시간 생성
        publish_at = generate_publish_time()

        # 4. drafts 테이블에 저장
        # keyword_id는 patterns에서 가져오거나 None (외래키 제약)
        actual_keyword_id = pattern_data.get("keyword_id") if pattern_data else None
        image_list = [
            {"path": img.get("path"), "prompt": img.get("prompt"), "filename": img.get("filename")}
            for img in content_result.get("images", [])
        ]
        draft_data = {
            "keyword_id": actual_keyword_id,
            "pattern_id": pattern_data.get("id") if pattern_data else None,
            "keyword": keyword,
            "title": content_result["title"],
            "body_html": content_result["body_html"],
            "meta_description": content_result.get("meta_description", ""),
            "tags": content_result.get("tags", []),
            "images": image_list,
            "status": "ready",
            "publish_at": publish_at.isoformat() if publish_at else None,
            "created_at": datetime.now().isoformat(),
        }

        inserted = supabase_insert("drafts", draft_data)

        result = {
            "success": True,
            "keyword_id": keyword_id,
            "title": content_result["title"],
            "char_count": len(content_result["body_html"]),
            "image_count": len(content_result.get("images", [])),
            "publish_at": publish_at.isoformat() if publish_at else None,
        }

        if inserted:
            result["draft_id"] = inserted.get("id")
            logger.info(f"드래프트 저장 완료: {result['draft_id']}")
        else:
            logger.warning("드래프트 DB 저장 실패")

        # 5. HTML 프리뷰 출력
        if output_html:
            from src.exporter import export_to_html

            html_path = export_to_html(
                title=content_result["title"],
                body_html=content_result["body_html"],
                tags=content_result.get("tags", []),
                images=[],  # body_html에 이미 이미지가 삽입되어 있으므로 중복 방지
                keyword=keyword,
            )
            result["html_path"] = str(html_path)
            logger.info(f"HTML 프리뷰 생성: {html_path}")

        output_json(result)

    except Exception as e:
        logger.error(f"생성 오류: {e}")
        output_error(str(e))


@cli.command("export")
@click.option("--draft-id", required=True, help="드래프트 ID (UUID)")
def export_draft(draft_id: str):
    """
    기존 드래프트를 HTML 프리뷰로 내보냅니다.

    DB에 저장된 드래프트 데이터를 로드하여 HTML 파일로 출력합니다.
    재생성 없이 기존 데이터만 사용합니다.
    """
    try:
        from src.exporter import export_to_html

        logger.info(f"드래프트 내보내기: draft_id={draft_id}")

        # DB에서 드래프트 로드
        drafts = supabase_select("drafts", {"id": draft_id})

        if not drafts:
            output_error(f"드래프트를 찾을 수 없습니다: {draft_id}")

        draft = drafts[0]

        # 키워드: draft에 직접 저장된 값 우선, 없으면 patterns 테이블 조회
        keyword = draft.get("keyword", "")
        if not keyword and draft.get("pattern_id"):
            patterns = supabase_select("patterns", {"id": draft["pattern_id"]})
            if patterns:
                keyword = patterns[0].get("keyword", "")

        html_path = export_to_html(
            title=draft["title"],
            body_html=draft["body_html"],
            tags=draft.get("tags", []),
            images=draft.get("images", []),
            keyword=keyword,
        )

        output_json({
            "success": True,
            "draft_id": draft_id,
            "html_path": str(html_path),
            "title": draft["title"],
        })

    except Exception as e:
        logger.error(f"내보내기 오류: {e}")
        output_error(str(e))


@cli.command()
@click.option("--draft-id", required=True, help="드래프트 ID (UUID)")
@click.option("--blog-account", default="A", help="블로그 계정 (A 또는 B)")
def publish(draft_id: str, blog_account: str):
    """
    드래프트ID로 블로그에 발행합니다.

    일일 한도와 발행 간격을 확인한 후 자동으로 발행합니다.
    """
    try:
        from src.publisher import (
            publish_draft,
            check_daily_limit,
            get_min_interval_ok,
        )
        from src.config import BLOG_ACCOUNTS

        logger.info(f"발행 시작: draft_id={draft_id}")

        # 1. 계정 정보 확인
        account = BLOG_ACCOUNTS.get(blog_account)

        blog_id = account.get("blog_id") if account else blog_account

        # 2. 발행 조건 확인
        if not check_daily_limit(blog_id):
            output_error("일일 발행 한도 초과")

        if not get_min_interval_ok(blog_id):
            output_error("최소 발행 간격 미충족")

        # 3. 발행 실행
        result = publish_draft(draft_id, blog_account)

        # 4. 결과 저장
        if result["success"]:
            # drafts 상태 업데이트
            supabase_update(
                "drafts",
                {"id": draft_id},
                {
                    "status": "published",
                    "published_at": datetime.now().isoformat(),
                    "naver_post_url": result.get("post_url"),
                },
            )

            # publish_logs 기록
            supabase_insert(
                "publish_logs",
                {
                    "draft_id": draft_id,
                    "blog_id": blog_id,
                    "action": "publish",
                    "status": "success",
                    "created_at": datetime.now().isoformat(),
                },
            )
        else:
            # 실패 로깅: retry_count 증분
            draft_data = (supabase_select("drafts", {"id": draft_id}) or [None])[0]
            current_retry = draft_data.get("retry_count", 0) if draft_data else 0
            supabase_update(
                "drafts",
                {"id": draft_id},
                {
                    "status": "failed",
                    "error_log": result.get("error"),
                    "retry_count": current_retry + 1,
                },
            )

            supabase_insert(
                "publish_logs",
                {
                    "draft_id": draft_id,
                    "blog_id": blog_id,
                    "action": "publish",
                    "status": "failed",
                    "error_detail": result.get("error"),
                    "created_at": datetime.now().isoformat(),
                },
            )

        output_json(result)

    except Exception as e:
        logger.error(f"발행 오류: {e}")
        output_error(str(e))


@cli.command("check-schedule")
def check_schedule():
    """
    발행 예정 드래프트를 확인하고 조건 충족 시 발행합니다.

    n8n 스케줄러에서 10분 간격으로 호출됩니다.
    """
    try:
        logger.info("스케줄 확인 시작")

        # 1. 발행 예정 드래프트 조회
        # publish_at <= now() AND status='ready'
        client = get_supabase_client()

        if not client:
            output_json({
                "success": True,
                "message": "Supabase 미설정",
                "published": [],
            })
            return

        import requests

        now = datetime.now().isoformat()
        url = f"{client['url']}/rest/v1/drafts"
        headers = {
            "apikey": client["key"],
            "Authorization": f"Bearer {client['key']}",
        }
        params = {
            "status": "eq.ready",
            "publish_at": f"lte.{now}",
            "select": "id,title,keyword_id",
            "order": "publish_at.asc",
            "limit": "5",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            output_json({
                "success": True,
                "message": "조회 실패",
                "published": [],
            })
            return

        drafts = response.json()

        if not drafts:
            output_json({
                "success": True,
                "message": "발행 예정 드래프트 없음",
                "published": [],
            })
            return

        # 2. 각 드래프트 발행
        published = []

        for draft in drafts:
            try:
                from src.publisher import publish_draft

                result = publish_draft(draft["id"])

                if result["success"]:
                    published.append({
                        "draft_id": draft["id"],
                        "title": draft["title"],
                        "post_url": result.get("post_url"),
                    })

                    # 상태 업데이트
                    supabase_update(
                        "drafts",
                        {"id": draft["id"]},
                        {
                            "status": "published",
                            "published_at": datetime.now().isoformat(),
                            "naver_post_url": result.get("post_url"),
                        },
                    )

            except Exception as e:
                logger.error(f"드래프트 발행 실패: {draft['id']} - {e}")

        output_json({
            "success": True,
            "message": f"{len(published)}개 발행 완료",
            "published": published,
        })

    except Exception as e:
        logger.error(f"스케줄 확인 오류: {e}")
        output_error(str(e))


if __name__ == "__main__":
    cli()
