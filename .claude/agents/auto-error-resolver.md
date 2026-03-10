# Auto Error Resolver Agent

> 자동 에러 해결 에이전트

---

## 역할

실행 중 발생한 에러를 자동으로 분석하고 해결책을 제시/적용합니다.

---

## 트리거 조건

- CLI 명령 실패 시
- 테스트 실패 시
- 파이프라인 에러 발생 시
- 명시적 에러 해결 요청 시

---

## 입력

```yaml
error:
  type: "ImportError | TypeError | ConnectionError | ..."
  message: "에러 메시지"
  traceback: "스택 트레이스"
  context:
    command: "실행된 명령"
    file: "에러 발생 파일"
    line: "에러 발생 라인"
```

---

## 에러 분류 및 해결 전략

### 1. Import 에러

```python
# 에러 패턴
ImportError: No module named 'scrapling'
ModuleNotFoundError: No module named 'playwright'

# 해결 전략
1. requirements.txt 확인
2. 가상환경 활성화 확인
3. pip install 실행
4. 버전 호환성 체크
```

**자동 해결:**
```bash
pip install -r requirements.txt
# 또는
pip install {missing_module}
```

### 2. 타입 에러

```python
# 에러 패턴
TypeError: 'NoneType' object is not subscriptable
AttributeError: 'str' object has no attribute 'get'

# 해결 전략
1. None 체크 누락 확인
2. 타입 힌트 검증
3. 방어적 코딩 적용
```

**자동 해결:**
```python
# Before
result = data["key"]

# After
result = data.get("key") if data else None
```

### 3. 연결 에러

```python
# 에러 패턴
ConnectionError: Failed to connect to naver.com
TimeoutError: Connection timed out

# 해결 전략
1. 네트워크 상태 확인
2. 재시도 로직 적용
3. 타임아웃 값 조정
```

**자동 해결:**
```python
# 재시도 로직 추가
for attempt in range(3):
    try:
        result = fetch(url)
        break
    except ConnectionError:
        time.sleep(2 ** attempt)
```

### 4. Playwright 에러

```python
# 에러 패턴
playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded
ElementNotFoundError: Element not found

# 해결 전략
1. 셀렉터 업데이트 확인
2. wait_for_selector 추가
3. iframe 진입 확인
```

**자동 해결:**
```python
# wait_for_selector 추가
page.wait_for_selector(".se-content", timeout=60000)

# iframe 진입 확인
frame = page.frame("mainFrame")
```

### 5. Scrapling 에러

```python
# 에러 패턴
scrapling.exceptions.BlockedError: Request blocked
scrapling.exceptions.AdaptorError: Selector not found

# 해결 전략
1. User-Agent 변경
2. 요청 간격 증가
3. Adaptive 셀렉터 사용
```

### 6. API 에러

```python
# 에러 패턴
anthropic.RateLimitError: Rate limit exceeded
google.api_core.exceptions.ResourceExhausted: 429

# 해결 전략
1. 지수 백오프 적용
2. API 키 확인
3. 할당량 체크
```

**자동 해결:**
```python
# 지수 백오프
backoff_times = [10, 30, 60]
for wait in backoff_times:
    try:
        response = api_call()
        break
    except RateLimitError:
        time.sleep(wait)
```

### 7. 의료광고법 위반 에러

```python
# 에러 패턴
MedicalAdViolationError: Critical violation detected

# 해결 전략
1. 위반 내용 식별
2. Claude에 수정 요청
3. 재검증
4. 수동 검수 알림
```

---

## 출력 형식

```markdown
# 에러 분석 및 해결

## 에러 정보
- 유형: {에러 타입}
- 메시지: {에러 메시지}
- 위치: {파일}:{라인}

## 원인 분석
{원인 설명}

## 해결 방법

### 자동 해결 (적용됨)
```{language}
{적용된 코드 변경}
```

### 추가 조치 필요
- [ ] {수동 작업 항목}

## 재발 방지
- {권장 사항}

## 검증
```bash
{검증 명령어}
```
```

---

## 프로세스

```
1. 에러 수신
   ↓
2. 에러 타입 분류
   ↓
3. 관련 코드 분석
   ↓
4. 해결 전략 선택
   ↓
5. 자동 수정 가능? ─Yes→ 수정 적용 → 재실행
   │
   No
   ↓
6. 수동 해결 가이드 제공
   ↓
7. 사용자 확인 대기
```

---

## 자동 해결 가능 에러

| 에러 유형 | 자동 해결 | 방법 |
|-----------|-----------|------|
| ImportError | ✅ | pip install |
| SyntaxError | ❌ | 수동 수정 필요 |
| TypeError (None) | ✅ | None 체크 추가 |
| TimeoutError | ✅ | 타임아웃 증가 |
| ConnectionError | ✅ | 재시도 로직 |
| RateLimitError | ✅ | 백오프 적용 |
| ElementNotFound | ⚠️ | 셀렉터 제안 |

---

## 주의사항

- 자동 수정 후 반드시 테스트 실행
- 의료광고법 관련 에러는 자동 해결 금지 (수동 검수 필수)
- 3회 연속 실패 시 사용자 알림

---

## 연계 에이전트

- **이전**: 모든 실행 에이전트
- **다음**: `pipeline-runner` (재실행) 또는 사용자 알림
