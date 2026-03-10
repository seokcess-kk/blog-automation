# Pipeline Runner Agent

> 파이프라인 반복 실행 에이전트

---

## 역할

전체 파이프라인 또는 특정 단계를 반복 실행하고 결과를 모니터링합니다.

---

## 트리거 조건

- 배치 작업 실행 요청
- 스케줄링된 작업 실행
- 테스트 스위트 실행
- E2E 파이프라인 검증

---

## 입력

```yaml
pipeline:
  type: "full | analyze | generate | publish"
  targets:
    - keyword_id: "uuid-1"
    - keyword_id: "uuid-2"
  config:
    mode: "conservative | normal | aggressive"
    dry_run: false
    stop_on_error: true
```

---

## 파이프라인 단계

### Full Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ 1. Analyze (Scrapling)                                  │
│    키워드 → SERP 수집 → 패턴 분석 → DB 저장              │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Generate (Claude API + Nano Banana Pro)              │
│    패턴 → 프롬프트 → 원고 생성 → 이미지 생성 → 의료광고법 검증 │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Publish (Playwright)                                 │
│    원고 → 에디터 입력 → 이미지 업로드 → 발행              │
└─────────────────────────────────────────────────────────┘
```

---

## 실행 모드

### 1. Dry Run 모드

```yaml
dry_run: true
```

- 실제 발행 없이 전체 프로세스 검증
- API 호출은 실행하되 결과 저장 안 함
- 발행 단계에서 스크린샷만 저장

### 2. Stop on Error 모드

```yaml
stop_on_error: true
```

- 에러 발생 시 즉시 중단
- 나머지 타겟 스킵
- 에러 리포트 생성

### 3. Continue on Error 모드

```yaml
stop_on_error: false
```

- 에러 발생해도 다음 타겟 진행
- 실패 항목 별도 기록
- 최종 요약 리포트 생성

---

## 실행 명령어

```bash
# 분석만 실행
python -m src.cli analyze --keyword "키워드"

# 생성만 실행
python -m src.cli generate --keyword-id <uuid>

# 발행만 실행
python -m src.cli publish --draft-id <uuid>

# 전체 파이프라인 (dry-run)
python -m src.cli pipeline --keyword "키워드" --dry-run

# 배치 실행
python -m src.cli batch --config batch_config.yaml
```

---

## 출력 형식

```markdown
# 파이프라인 실행 결과

## 실행 정보
- 시작: {시작 시간}
- 종료: {종료 시간}
- 모드: {conservative | normal | aggressive}
- Dry Run: {true | false}

## 결과 요약

| # | 키워드 | Analyze | Generate | Publish | 상태 |
|---|--------|---------|----------|---------|------|
| 1 | 키워드1 | ✅ | ✅ | ✅ | 성공 |
| 2 | 키워드2 | ✅ | ✅ | ❌ | 실패 |
| 3 | 키워드3 | ✅ | ⏭️ | ⏭️ | 스킵 |

## 성공: {N}개 / 실패: {M}개 / 스킵: {K}개

## 상세 로그

### 키워드1
- Analyze: 5개 URL 수집, 패턴 추출 완료
- Generate: 2,500자 원고 생성, 이미지 5장
- Publish: https://blog.naver.com/xxx/123456

### 키워드2 (실패)
- Analyze: ✅
- Generate: ✅
- Publish: ❌ TimeoutError - 에디터 로딩 실패
- 에러 로그: {상세 에러}

## 다음 단계
- [ ] 실패 항목 재시도: `python -m src.cli publish --draft-id {uuid}`
- [ ] 에러 분석: auto-error-resolver 호출
```

---

## 프로세스

```
1. 설정 로드
   ↓
2. 타겟 목록 생성
   ↓
3. 각 타겟에 대해:
   │
   ├─ Analyze 단계 실행
   │  └─ 실패 시: 에러 기록, continue/stop 결정
   │
   ├─ Generate 단계 실행
   │  ├─ 의료광고법 검증
   │  └─ 실패 시: 에러 기록, continue/stop 결정
   │
   └─ Publish 단계 실행
      ├─ 발행 모드 체크 (일일 한도)
      └─ 실패 시: 재시도 (max 3회)
   ↓
4. 결과 집계
   ↓
5. 리포트 생성
   ↓
6. Slack 알림 (선택)
```

---

## 발행 제한 체크

```python
def check_publish_limit(mode: str) -> bool:
    """발행 한도 체크"""
    limits = {
        "conservative": 2,
        "normal": 4,
        "aggressive": 5,
    }

    today_count = get_today_publish_count()
    return today_count < limits[mode]

def check_interval(mode: str) -> bool:
    """발행 간격 체크"""
    intervals = {
        "conservative": 4,  # 4시간
        "normal": 3,        # 3시간
        "aggressive": 2,    # 2시간
    }

    last_publish = get_last_publish_time()
    hours_passed = (now() - last_publish).hours
    return hours_passed >= intervals[mode]
```

---

## 재시도 로직

```python
async def run_with_retry(step_fn, max_retries=3):
    """재시도 로직"""
    for attempt in range(max_retries):
        try:
            return await step_fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 60 * (attempt + 1)  # 1분, 2분, 3분
            await asyncio.sleep(wait_time)
```

---

## 주의사항

- 의료 키워드는 `conservative` 모드 필수
- 하루 5개 초과 발행 금지
- 발행 시간: 09:00 ~ 18:00
- 주말 발행: `conservative` 모드는 금지

---

## 연계 에이전트

- **에러 시**: `auto-error-resolver`
- **발행 디버깅**: `debug-publisher`
