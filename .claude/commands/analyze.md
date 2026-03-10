# /analyze

> 키워드 분석 명령어

---

## 설명

지정된 키워드에 대해 네이버 상위노출 패턴을 분석합니다.

---

## 사용법

```
/analyze <키워드> [옵션]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--count` | 5 | 분석할 상위 URL 개수 |
| `--save` | true | DB 저장 여부 |
| `--verbose` | false | 상세 출력 |

---

## 실행 내용

1. **SERP 수집** (Scrapling)
   - 네이버 검색 결과 수집
   - 상위 N개 블로그 URL 추출

2. **콘텐츠 파싱**
   - 각 URL 본문 구조 분석
   - 글자수, 이미지수, 소제목 추출

3. **패턴 추출**
   - 통계 계산 (평균, 분포)
   - 키워드 배치 패턴 분석
   - 관련 키워드 추출

4. **결과 저장**
   - patterns 테이블에 저장
   - JSON 형식 출력

---

## 출력 예시

```json
{
  "keyword": "강남 피부과",
  "analyzed_urls": 5,
  "pattern": {
    "avg_char_count": 2500,
    "avg_image_count": 7,
    "avg_heading_count": 5,
    "title_patterns": ["지역 + 키워드", "숫자 활용"],
    "keyword_placement": {
      "title": true,
      "first_paragraph": true,
      "headings": 3
    },
    "related_keywords": ["피부관리", "여드름", "피부과 추천"]
  }
}
```

---

## 관련 모듈

- `src/analyzer/serp_collector.py`
- `src/analyzer/content_parser.py`
- `src/analyzer/pattern_extractor.py`

---

## 주의사항

- Scrapling 전용 (Playwright 사용 금지)
- 요청 간격 1초 이상 유지
- 의료 키워드는 `medical-ad-law` 스킬 자동 활성화
