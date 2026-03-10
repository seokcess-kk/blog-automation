"""
의료광고법 위반 표현 검증 모듈

의료법 제56조 및 시행령 제23조에 근거하여 의료광고 금지 표현을 검증합니다.

법령 근거:
- 의료법 제56조 (의료광고의 금지 등)
- 의료법 제57조 (의료광고의 심의)
- 시행령 제23조 (의료광고의 금지 기준)
- 벌칙: 제89조 (1년 이하 징역 / 1천만원 이하 벌금)
"""

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """의료광고법 위반 정보를 담는 데이터 클래스."""

    word: str
    """위반 단어/패턴"""

    position: int
    """텍스트 내 위치 (문자 인덱스)"""

    category: str
    """위반 카테고리명"""

    severity: Literal["critical", "warning"]
    """심각도: 'critical' (발행 불가) 또는 'warning' (경고 후 진행)"""

    law_reference: str
    """법령 근거 (예: '법56조②2호, 시행령23조①2호')"""

    suggestion: str
    """대체 표현 제안"""


# =============================================================================
# 금칙어 데이터베이스
# 법령 근거: .claude/skills/medical-ad-law/resources/ 참조
# =============================================================================

# 카테고리 1: 치료효과 오인 유발 (critical)
# 법근거: 법56조②2호, 시행령23조①2호
_CAT1_TREATMENT_EFFECT: dict[str, str] = {
    "확실": "효과를 기대할 수 있는",
    "보장": "도움이 될 수 있는",
    "완치": "개선을 기대할 수 있는",
    "100%": "높은 만족도의",
    "반드시 효과": "효과를 기대할 수 있는",
    "틀림없이": "긍정적인 결과를 기대할 수 있는",
    "후기": "정보",
    "체험기": "안내",
    "경험담": "소개",
    "직접 해본": "일반적인",
    "실제 효과": "기대할 수 있는 효과",
    "치료 후기": "치료 안내",
}

# 카테고리 2: 거짓/과장 표현 (critical)
# 법근거: 법56조②3,8호, 시행령23조①3,8호
_CAT2_FALSE_EXAGGERATION: dict[str, str] = {
    "최고": "우수한",
    "최초": "차별화된",
    "유일": "특화된",
    "독보적": "전문적인",
    "압도적": "뛰어난",
    "최상의": "양질의",
    "국내 유일": "국내 전문",
    "획기적": "새로운",
    "혁신적": "개선된",
    "기적의": "효과적인",
    "놀라운 효과": "긍정적인 효과",
    "완벽한": "높은 수준의",
    "부작용 없는": "부작용을 최소화한",
    "통증 없는": "통증을 최소화한",
    "100% 안전": "안전성을 고려한",
    "무조건": "일반적으로",
}

# 카테고리 3: 비교/비방 (critical)
# 법근거: 법56조②4,5호, 시행령23조①4,5호
_CAT3_COMPARISON_PATTERNS: list[str] = [
    r"보다\s*우수",
    r"보다\s*효과적",
    r"보다\s*안전",
    r"보다\s*좋은",
    r"보다\s*뛰어난",
    r"타\s*병원",
    r"다른\s*병원",
    r"경쟁\s*병원",
]

# 카테고리 5: 무자격 명칭 (critical)
# 법근거: 법56조②9호
_CAT5_UNQUALIFIED_TITLE: dict[str, str] = {
    "명의": "전문의",
    "대한민국 대표": "전문",
    "국내 최고 권위": "전문",
    "세계적 권위": "국제 경험이 있는",
}

# 카테고리 8: 소비자 유인 (warning)
# 법근거: 법56조②13호, 시행령23조①13호
_CAT8_CONSUMER_ATTRACTION: dict[str, str] = {
    "무료 상담": "상담 안내",
    "할인 이벤트": "안내",
    "특별 할인": "안내",
    "무료 체험": "체험 안내",
    "파격 할인": "안내",
    "이벤트 가격": "안내",
}

# 카테고리 4 체크용: 시술/한약 키워드
_PROCEDURE_KEYWORDS: list[str] = [
    "시술",
    "수술",
    "주사",
    "레이저",
    "필러",
    "보톡스",
    "리프팅",
    "지방흡입",
    "임플란트",
    "라식",
    "라섹",
    "한약",
    "탕약",
    "침",
    "뜸",
    "부항",
    "추나",
    "약침",
]

# 부작용 관련 표현 (있으면 warning 해제)
_SIDE_EFFECT_MENTIONS: list[str] = [
    "부작용",
    "개인차",
    "개인에 따라",
    "차이가 있을 수",
    "주의사항",
    "위험",
    "합병증",
    "출혈",
    "감염",
    "붓기",
    "멍",
    "통증이 있을 수",
]

# 기사 형태 키워드
_ARTICLE_STYLE_KEYWORDS: list[str] = [
    "기자",
    "취재",
    "보도",
    "기사",
    "인터뷰",
    "특집",
]

# 연락처 패턴
_CONTACT_PATTERNS: list[str] = [
    r"\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4}",  # 전화번호
    r"[가-힣]+구\s*[가-힣]+동",  # 주소 (구/동)
    r"[가-힣]+시\s*[가-힣]+구",  # 주소 (시/구)
    r"[가-힣]+로\s*\d+",  # 도로명
]


def _check_keyword_violations(
    text: str,
    keywords: dict[str, str],
    category: str,
    severity: Literal["critical", "warning"],
    law_reference: str,
) -> list[Violation]:
    """키워드 기반 위반 검사."""
    violations = []
    text_lower = text.lower()

    for keyword, suggestion in keywords.items():
        keyword_lower = keyword.lower()
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            violations.append(
                Violation(
                    word=keyword,
                    position=pos,
                    category=category,
                    severity=severity,
                    law_reference=law_reference,
                    suggestion=suggestion,
                )
            )
            start = pos + 1

    return violations


def _check_pattern_violations(
    text: str,
    patterns: list[str],
    category: str,
    severity: Literal["critical", "warning"],
    law_reference: str,
    suggestion: str,
) -> list[Violation]:
    """정규식 패턴 기반 위반 검사."""
    violations = []

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            violations.append(
                Violation(
                    word=match.group(),
                    position=match.start(),
                    category=category,
                    severity=severity,
                    law_reference=law_reference,
                    suggestion=suggestion,
                )
            )

    return violations


def _check_side_effect_omission(text: str) -> list[Violation]:
    """카테고리 4: 부작용 정보 누락 검사.

    시술/한약 언급이 있으면서 부작용 관련 언급이 없으면 warning.
    """
    violations = []

    # 시술/한약 키워드 존재 여부
    has_procedure = any(kw in text for kw in _PROCEDURE_KEYWORDS)
    if not has_procedure:
        return violations

    # 부작용 언급 존재 여부
    has_side_effect_mention = any(
        mention in text for mention in _SIDE_EFFECT_MENTIONS
    )
    if has_side_effect_mention:
        return violations

    # 시술 키워드 위치 찾기
    for kw in _PROCEDURE_KEYWORDS:
        if kw in text:
            pos = text.find(kw)
            violations.append(
                Violation(
                    word=kw,
                    position=pos,
                    category="부작용 정보 누락",
                    severity="warning",
                    law_reference="법56조②7호, 시행령23조①7호",
                    suggestion=f"'{kw}' 언급 시 '개인에 따라 차이가 있을 수 있습니다' 등 부작용/개인차 안내 추가 권장",
                )
            )
            break  # 한 번만 경고

    return violations


def _check_article_disguise(text: str) -> list[Violation]:
    """카테고리 6: 기사/전문가 위장 검사.

    기사 형태 표현 + 연락처/주소 동시 노출 시 warning.
    """
    violations = []

    # 기사 형태 키워드 존재 여부
    article_keyword = None
    article_pos = -1
    for kw in _ARTICLE_STYLE_KEYWORDS:
        if kw in text:
            article_keyword = kw
            article_pos = text.find(kw)
            break

    if not article_keyword:
        return violations

    # 연락처 패턴 존재 여부
    has_contact = any(
        re.search(pattern, text) for pattern in _CONTACT_PATTERNS
    )

    if has_contact:
        violations.append(
            Violation(
                word=article_keyword,
                position=article_pos,
                category="기사/전문가 위장 광고",
                severity="warning",
                law_reference="법56조②10호, 시행령23조①10호",
                suggestion="기사 형태 콘텐츠와 병원 연락처/주소를 함께 노출하지 마세요",
            )
        )

    return violations


def _check_weight_loss_claims(text: str) -> list[Violation]:
    """체중 감량 단정 표현 검사 (예: 10kg 감량).

    법근거: 법56조②2호, 시행령23조①2호
    """
    violations = []
    pattern = r"\d+\s*kg\s*감량"

    for match in re.finditer(pattern, text, re.IGNORECASE):
        violations.append(
            Violation(
                word=match.group(),
                position=match.start(),
                category="치료효과 오인 유발",
                severity="critical",
                law_reference="법56조②2호, 시행령23조①2호",
                suggestion="구체적 수치 대신 '체중 관리에 도움이 될 수 있는' 등으로 표현",
            )
        )

    return violations


def check_violations(text: str) -> list[Violation]:
    """의료광고법 위반 표현을 검증합니다.

    Args:
        text: 검증할 텍스트

    Returns:
        위반 항목 리스트. 위반이 없으면 빈 리스트.

    Example:
        >>> violations = check_violations("이 시술은 확실한 효과가 있습니다")
        >>> for v in violations:
        ...     print(f"{v.severity}: {v.word} - {v.law_reference}")
        critical: 확실 - 법56조②2호, 시행령23조①2호
    """
    violations: list[Violation] = []

    # 카테고리 1: 치료효과 오인 유발 (critical)
    violations.extend(
        _check_keyword_violations(
            text,
            _CAT1_TREATMENT_EFFECT,
            "치료효과 오인 유발",
            "critical",
            "법56조②2호, 시행령23조①2호",
        )
    )

    # 카테고리 2: 거짓/과장 표현 (critical)
    violations.extend(
        _check_keyword_violations(
            text,
            _CAT2_FALSE_EXAGGERATION,
            "거짓/과장 표현",
            "critical",
            "법56조②3,8호, 시행령23조①3,8호",
        )
    )

    # 카테고리 3: 비교/비방 (critical)
    violations.extend(
        _check_pattern_violations(
            text,
            _CAT3_COMPARISON_PATTERNS,
            "비교/비방 광고",
            "critical",
            "법56조②4,5호, 시행령23조①4,5호",
            "비교 표현을 삭제하고 자체 장점만 언급",
        )
    )

    # 카테고리 5: 무자격 명칭 (critical)
    violations.extend(
        _check_keyword_violations(
            text,
            _CAT5_UNQUALIFIED_TITLE,
            "무자격 명칭 표방",
            "critical",
            "법56조②9호",
        )
    )

    # 카테고리 8: 소비자 유인 (warning)
    violations.extend(
        _check_keyword_violations(
            text,
            _CAT8_CONSUMER_ATTRACTION,
            "소비자 유인",
            "warning",
            "법56조②13호, 시행령23조①13호",
        )
    )

    # 카테고리 4: 부작용 정보 누락 (warning)
    violations.extend(_check_side_effect_omission(text))

    # 카테고리 6: 기사/전문가 위장 (warning)
    violations.extend(_check_article_disguise(text))

    # 추가: 체중 감량 단정 표현 (critical)
    violations.extend(_check_weight_loss_claims(text))

    # 위치순 정렬
    violations.sort(key=lambda v: v.position)

    if violations:
        critical_count = sum(1 for v in violations if v.severity == "critical")
        warning_count = sum(1 for v in violations if v.severity == "warning")
        logger.warning(
            f"의료광고법 위반 검출: critical {critical_count}건, warning {warning_count}건"
        )

    return violations


def has_critical(violations: list[Violation]) -> bool:
    """critical 심각도 위반 존재 여부를 반환합니다.

    Args:
        violations: 위반 리스트

    Returns:
        critical 위반이 하나라도 있으면 True

    Example:
        >>> violations = check_violations("최고의 시술")
        >>> if has_critical(violations):
        ...     print("발행 불가: 수정 필요")
    """
    return any(v.severity == "critical" for v in violations)


def get_violation_summary(violations: list[Violation]) -> str:
    """위반 요약 텍스트를 생성합니다 (Slack 알림용).

    Args:
        violations: 위반 리스트

    Returns:
        마크다운 형식의 위반 요약 텍스트

    Example:
        >>> violations = check_violations("확실한 효과를 보장합니다")
        >>> print(get_violation_summary(violations))
        *의료광고법 위반 검출*
        - [critical] '확실' (치료효과 오인 유발)
        - [critical] '보장' (치료효과 오인 유발)
    """
    if not violations:
        return "위반 없음"

    critical_violations = [v for v in violations if v.severity == "critical"]
    warning_violations = [v for v in violations if v.severity == "warning"]

    lines = ["*의료광고법 위반 검출*"]

    if critical_violations:
        lines.append(f"\n:red_circle: *Critical ({len(critical_violations)}건)* - 수정 필수")
        for v in critical_violations:
            lines.append(f"  - `{v.word}` ({v.category})")
            lines.append(f"    법령: {v.law_reference}")
            lines.append(f"    대체: {v.suggestion}")

    if warning_violations:
        lines.append(f"\n:warning: *Warning ({len(warning_violations)}건)* - 검토 권장")
        for v in warning_violations:
            lines.append(f"  - `{v.word}` ({v.category})")
            lines.append(f"    {v.suggestion}")

    return "\n".join(lines)
