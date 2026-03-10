# Medical Ad Law (의료광고법)

> **enforcement: block**
> 의료광고법 준수 규칙 — 위반 시 작업 중단

---

## 1. 적용 법령

| 법령 | 조항 | 내용 |
|------|------|------|
| 의료법 | 제56조 | 의료광고의 금지 등 |
| 의료법 | 제57조 | 의료광고의 심의 |
| 시행령 | 제23조 | 의료광고의 금지 기준 |
| 의료법 | 제89조 | **벌칙: 1년 이하 징역 / 1천만원 이하 벌금** |
| 의료법 | 제67조 | **과징금: 5천만원 이하** |

**원문 참조:** `./resources/law-article-56.md`, `./resources/law-article-57.md`, `./resources/enforcement-23.md`

---

## 2. 금지 카테고리 (8개)

### 2.1 Critical (자동 차단 — 수정 없이 발행 불가)

| # | 카테고리 | 법령 근거 | 설명 |
|---|----------|-----------|------|
| 1 | 치료효과 오인 유발 | 법56조②2호, 시행령23조①2호 | 환자 치료경험담, 효과 단정 |
| 2 | 거짓/과장 표현 | 법56조②3,8호, 시행령23조①3,8호 | 객관적 사실과 다른 내용 |
| 3 | 비교/비방 | 법56조②4,5호, 시행령23조①4,5호 | 타 의료기관 비교/비방 |
| 5 | 법적 근거 없는 자격 | 법56조②9호 | 무자격 명칭 표방 |

### 2.2 Warning (경고 — 로깅 후 진행 가능)

| # | 카테고리 | 법령 근거 | 설명 |
|---|----------|-----------|------|
| 4 | 부작용 정보 누락 | 법56조②7호, 시행령23조①7호 | 중요 부작용 정보 미고지 |
| 6 | 기사/전문가 위장 | 법56조②10호, 시행령23조①10호 | 기사 형태 + 연락처 노출 |
| 7 | 인증/보증 부당 사용 | 법56조②14호 | 법정 예외 외 인증 표시 |
| 8 | 소비자 유인 (할인) | 법56조②13호, 시행령23조①13호 | 허위/불명확 할인 정보 |

---

## 3. 금칙어 목록

### 3.1 Critical 금칙어 (자동 차단)

```python
CRITICAL_FORBIDDEN_WORDS = [
    # 2호 근거: 치료효과 단정 + 경험담
    "확실", "보장", "완치", "100%", "반드시 효과", "틀림없이",
    "후기", "체험기", "경험담", "직접 해본", "실제 효과", "치료 후기",
    "OOkg 감량", "며칠 만에", "단 N회",

    # 3호+8호 근거: 거짓/과장
    "최고", "최초", "유일", "독보적", "압도적", "최상의", "국내 유일",
    "획기적", "혁신적", "기적의", "놀라운 효과", "완벽한",
    "부작용 없는", "통증 없는", "100% 안전", "무조건",
    "세계 최초", "아시아 최초", "국내 최초",

    # 4호+5호 근거: 비교/비방
    "~보다 우수", "~보다 효과적", "~보다 안전",
    "타 병원과 달리", "다른 곳에서는",

    # 9호 근거: 무자격 명칭
    "명의", "대한민국 대표", "최고의 의사",
]
```

### 3.2 Warning 금칙어 (경고 후 진행)

```python
WARNING_WORDS = [
    # 7호 근거: 부작용 누락 패턴 탐지
    # (시술/한약 언급 시 부작용 미언급 감지)

    # 10호 근거: 기사 위장
    # (기사 형태 + 연락처/주소 동시 노출)

    # 13호 근거: 소비자 유인
    "무료 상담", "할인 이벤트", "특별 할인", "무료 체험",
    "선착순", "한정 수량", "오늘만",

    # 14호 근거: 인증 부당 사용
    # (법정 예외 외 인증/보증/추천 표시)
]
```

---

## 4. 검증 프로세스

```
┌─────────────────────────────────────────────────────────┐
│                    원고 생성 완료                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│         medical_ad_checker.check_violations(text)        │
└─────────────────────────┬───────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ Critical │  │ Warning  │  │   Pass   │
     │  위반    │  │   Only   │  │  (통과)  │
     └────┬─────┘  └────┬─────┘  └────┬─────┘
          │             │             │
          ▼             ▼             ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │Claude 수정 │ │ 로깅 +     │ │  정상 발행  │
   │ 재요청     │ │ 주석 추가  │ │            │
   │ (max 2회)  │ │            │ │            │
   └────┬───────┘ └────┬───────┘ └────────────┘
        │              │
        ▼              ▼
   ┌────────────┐ ┌────────────┐
   │여전히 위반?│ │  정상 발행  │
   │    │       │ │            │
   │ Yes│ No    │ │            │
   └──┬─┴───────┘ └────────────┘
      │
      ▼
┌─────────────────────┐
│ 수동 검수 + Slack   │
│ 알림 (발행 중단)    │
└─────────────────────┘
```

---

## 5. 검증 코드 패턴

### 5.1 medical_ad_checker.py 구조

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"

@dataclass
class Violation:
    severity: Severity
    category: str
    matched_text: str
    law_reference: str
    suggestion: str

def check_violations(text: str) -> List[Violation]:
    """의료광고법 위반 검사"""
    violations = []

    # Critical 검사
    violations.extend(_check_treatment_effect(text))
    violations.extend(_check_false_exaggeration(text))
    violations.extend(_check_comparison(text))
    violations.extend(_check_unqualified_title(text))

    # Warning 검사
    violations.extend(_check_side_effect_omission(text))
    violations.extend(_check_article_disguise(text))
    violations.extend(_check_improper_certification(text))
    violations.extend(_check_consumer_inducement(text))

    return violations

def has_critical_violation(violations: List[Violation]) -> bool:
    """Critical 위반 존재 여부"""
    return any(v.severity == Severity.CRITICAL for v in violations)
```

### 5.2 검증 결과 처리

```python
def process_draft(draft_id: str, content: str) -> Tuple[bool, str]:
    """원고 검증 및 처리"""
    violations = check_violations(content)

    if not violations:
        return True, content

    if has_critical_violation(violations):
        # Critical: Claude에 수정 요청
        for attempt in range(2):
            content = request_revision(content, violations)
            violations = check_violations(content)
            if not has_critical_violation(violations):
                break

        if has_critical_violation(violations):
            # 여전히 위반: 수동 검수
            notify_slack(draft_id, violations)
            return False, content

    # Warning만 있는 경우: 로깅 후 진행
    log_warnings(draft_id, violations)
    return True, add_disclaimer(content)
```

---

## 6. 수정 요청 프롬프트

```python
REVISION_PROMPT = """
다음 원고에서 의료광고법 위반 표현을 수정해주세요.

## 위반 사항
{violations}

## 원본 원고
{content}

## 수정 규칙
1. 위반 표현을 법적으로 안전한 표현으로 대체
2. "개인에 따라 효과가 다를 수 있습니다" 등 면책 문구 추가
3. 과장 표현 → 객관적 사실 기반 표현으로 수정
4. 치료 효과 단정 → 가능성/기대 표현으로 완화

## 출력 형식
수정된 원고만 JSON 형식으로 반환
"""
```

---

## 7. 권장 표현

### 7.1 금지 → 권장 변환

| 금지 표현 | 권장 표현 |
|-----------|-----------|
| "완치됩니다" | "개선에 도움이 될 수 있습니다" |
| "100% 효과" | "많은 분들이 만족하셨습니다" |
| "부작용 없음" | "개인에 따라 다를 수 있습니다" |
| "최고의 치료" | "전문적인 진료" |
| "기적의 효과" | "체계적인 관리" |
| "확실한 결과" | "기대되는 결과" |

### 7.2 면책 문구

```
※ 시술 결과는 개인에 따라 차이가 있을 수 있습니다.
※ 정확한 진단과 치료는 전문의 상담 후 결정됩니다.
※ 본 정보는 참고용이며, 의료적 조언을 대체하지 않습니다.
```

---

## 8. 프롬프트 필수 포함 사항

`prompts/system_prompt.md`에 반드시 포함:

```markdown
## 의료광고법 준수 (필수)

아래 표현은 의료법 제56조 위반으로 **절대 사용 금지**:

1. 치료효과 단정: "완치", "확실", "100%", "보장"
2. 환자 경험담: "후기", "체험기", "직접 해본"
3. 과장 표현: "최고", "최초", "유일", "기적의"
4. 비교/비방: "~보다 우수", 타 병원명 언급
5. 무자격 명칭: "명의", "대한민국 대표"

대신 다음 표현 사용:
- "개선에 도움이 될 수 있습니다"
- "개인에 따라 차이가 있습니다"
- "전문의 상담을 권장합니다"

**위반 시 벌칙: 1년 이하 징역 또는 1천만원 이하 벌금**
```

---

## 9. 위반 시 처리

### 9.1 자동 처리

```
Critical 위반 감지 → 발행 자동 중단 → Slack 알림 → 수동 검수 대기
```

### 9.2 수동 검수 체크리스트

```
[ ] 위반 표현 식별
[ ] 법령 근거 확인 (제56조, 시행령 제23조)
[ ] 수정안 작성
[ ] 수정 후 재검증
[ ] 발행 승인/거부 결정
```

---

## 10. 참고 자료

- [의료법 제56조 원문](./resources/law-article-56.md)
- [의료법 제57조 원문](./resources/law-article-57.md)
- [시행령 제23조 원문](./resources/enforcement-23.md)
- [보건복지부 의료광고 가이드라인](https://www.mohw.go.kr/)
