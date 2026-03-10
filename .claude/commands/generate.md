# /generate

> 콘텐츠 생성 명령어

---

## 설명

분석된 패턴을 기반으로 SEO 최적화된 원고와 이미지를 생성합니다.

---

## 사용법

```
/generate <keyword-id> [옵션]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--images` | 5 | 생성할 이미지 수 |
| `--check` | true | 의료광고법 검증 |
| `--save` | true | DB 저장 여부 |

---

## 실행 내용

1. **패턴 로드**
   - keyword_id로 patterns 테이블 조회
   - 분석 데이터 로드

2. **프롬프트 빌드**
   - System Prompt 로드
   - Pattern Injection 적용
   - 3계층 프롬프트 조립

3. **원고 생성** (Claude API)
   - claude-sonnet-4-20250514 호출
   - JSON 구조화 출력
   - 제목, 본문, 태그 생성

4. **의료광고법 검증**
   - `medical_ad_checker.check_violations()`
   - Critical 위반 시 수정 재요청 (max 2회)
   - Warning 시 면책 문구 추가

5. **이미지 생성** (Nano Banana Pro)
   - gemini-3-pro-image-preview 호출
   - base64 디코딩 → JPEG 저장
   - EXIF 메타데이터 삽입

6. **결과 저장**
   - drafts 테이블에 저장
   - 이미지 파일 저장

---

## 출력 예시

```json
{
  "draft_id": "uuid-xxx",
  "keyword_id": "uuid-yyy",
  "title": "강남 피부과 추천 TOP 5 - 2025 최신 정보",
  "body_char_count": 2800,
  "images": [
    {"path": "images/uuid-1.jpg", "exif": true},
    {"path": "images/uuid-2.jpg", "exif": true}
  ],
  "tags": ["강남피부과", "피부과추천", "강남", "피부관리"],
  "medical_check": {
    "status": "pass",
    "warnings": ["부작용 정보 추가 권장"]
  }
}
```

---

## 관련 모듈

- `src/generator/prompt_builder.py`
- `src/generator/content_generator.py`
- `src/generator/image_generator.py`
- `src/utils/medical_ad_checker.py`
- `src/utils/exif.py`

---

## 주의사항

- 의료 키워드는 반드시 `medical-ad-law` 검증 필수
- Critical 위반 시 발행 불가
- 이미지 생성 429 에러 시 자동 백오프
