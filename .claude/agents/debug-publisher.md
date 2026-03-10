# Debug Publisher Agent

> 발행 디버깅 에이전트

---

## 역할

Playwright 기반 발행 프로세스의 문제를 진단하고 해결합니다.

---

## 트리거 조건

- 발행 실패 시
- 에디터 조작 오류 시
- 로그인 실패 시
- 명시적 발행 디버깅 요청 시

---

## 입력

```yaml
error:
  type: "login | editor | upload | publish | unknown"
  message: "에러 메시지"
  screenshot: "스크린샷 경로 (있는 경우)"
  context:
    draft_id: "uuid"
    step: "실패한 단계"
    browser_logs: "콘솔 로그"
```

---

## 진단 체크리스트

### 1. 로그인 문제

```markdown
## 로그인 진단

### 세션 확인
[ ] user_data_dir 존재 여부
[ ] 세션 쿠키 유효성
[ ] 마지막 로그인 시간

### 캡차 확인
[ ] 캡차 발생 여부
[ ] IP 차단 여부

### 자격 증명
[ ] .env 파일 확인
[ ] 비밀번호 변경 여부

### 해결 방법
1. 세션 만료 → 수동 재로그인 후 user_data_dir 갱신
2. 캡차 발생 → 수동 해결 후 재시도
3. IP 차단 → VPN/프록시 변경 또는 24시간 대기
```

### 2. 에디터 문제

```markdown
## 에디터 진단

### iframe 진입
[ ] mainFrame 로딩 완료
[ ] .se-content 요소 존재
[ ] 에디터 모드 (스마트에디터 3.0)

### 셀렉터 확인
[ ] .se-title-text 존재
[ ] .se-text-paragraph 존재
[ ] 툴바 버튼 존재

### 타이밍 이슈
[ ] 충분한 대기 시간
[ ] 네트워크 상태

### 해결 방법
1. iframe 미로딩 → wait_for_selector 타임아웃 증가
2. 셀렉터 변경 → naver-editor.md 업데이트
3. 타이밍 이슈 → human_delay 증가
```

### 3. 이미지 업로드 문제

```markdown
## 이미지 업로드 진단

### 파일 확인
[ ] 파일 존재 여부
[ ] 파일 크기 (1MB 이하)
[ ] 파일 형식 (JPEG/PNG)
[ ] EXIF 데이터 유효성

### 업로드 프로세스
[ ] 업로드 버튼 클릭
[ ] 파일 선택 다이얼로그
[ ] 업로드 진행 상태
[ ] 업로드 완료 확인

### 해결 방법
1. 파일 크기 초과 → 이미지 압축
2. 형식 오류 → JPEG로 변환
3. 업로드 실패 → 재시도 (최대 3회)
```

### 4. 발행 문제

```markdown
## 발행 진단

### 발행 버튼
[ ] .publish_btn 존재
[ ] 버튼 활성화 상태
[ ] 클릭 이벤트 발생

### 확인 다이얼로그
[ ] .confirm_btn 존재
[ ] 다이얼로그 표시

### 발행 완료
[ ] URL 변경 확인 (PostView.naver)
[ ] 발행 성공 메시지

### 해결 방법
1. 버튼 비활성화 → 필수 필드 확인 (제목, 본문)
2. 다이얼로그 미표시 → 팝업 차단 확인
3. URL 미변경 → 발행 실패, 에러 메시지 확인
```

---

## 디버깅 도구

### 스크린샷 캡처

```python
def capture_debug_screenshot(page, name: str):
    """디버깅용 스크린샷 저장"""
    timestamp = int(time.time())
    path = f"debug/screenshots/{name}_{timestamp}.png"
    page.screenshot(path=path, full_page=True)
    return path
```

### 콘솔 로그 캡처

```python
def setup_console_logging(page):
    """브라우저 콘솔 로그 캡처"""
    logs = []

    def log_handler(msg):
        logs.append({
            "type": msg.type,
            "text": msg.text,
            "time": time.time()
        })

    page.on("console", log_handler)
    return logs
```

### 네트워크 모니터링

```python
def setup_network_logging(page):
    """네트워크 요청 모니터링"""
    requests = []

    def request_handler(request):
        requests.append({
            "url": request.url,
            "method": request.method,
            "time": time.time()
        })

    page.on("request", request_handler)
    return requests
```

---

## 출력 형식

```markdown
# 발행 디버깅 결과

## 에러 정보
- 유형: {login | editor | upload | publish}
- 단계: {실패한 단계}
- 시간: {발생 시간}

## 진단 결과

### 확인된 문제
- {문제 1}: {상세 설명}
- {문제 2}: {상세 설명}

### 스크린샷
![에러 스크린샷]({스크린샷 경로})

### 콘솔 로그
```
{관련 콘솔 로그}
```

## 해결 방법

### 자동 해결 (적용됨)
- {적용된 해결책}

### 수동 조치 필요
1. {수동 작업 1}
2. {수동 작업 2}

## 재시도
```bash
python -m src.cli publish --draft-id {draft_id} --debug
```

## 셀렉터 업데이트 필요 시
```
파일: .claude/skills/playwright-guidelines/resources/naver-editor.md
변경: {셀렉터 변경 내용}
```
```

---

## 프로세스

```
1. 에러 정보 수신
   ↓
2. 에러 유형 분류
   ↓
3. 해당 진단 체크리스트 실행
   ↓
4. 스크린샷/로그 분석
   ↓
5. 문제 원인 식별
   ↓
6. 해결책 제시/적용
   ↓
7. 재시도 또는 수동 조치 안내
```

---

## 일반적인 해결책

### 세션 갱신

```bash
# 브라우저 데이터 백업
cp -r browser_data browser_data_backup

# 수동 로그인 실행
python -m src.cli login --manual

# 세션 확인
python -m src.cli check-session
```

### 셀렉터 업데이트

```python
# 현재 페이지 HTML 덤프
def dump_html(page, name: str):
    html = page.content()
    with open(f"debug/{name}.html", "w") as f:
        f.write(html)

# 셀렉터 테스트
def test_selector(page, selector: str):
    elements = page.query_selector_all(selector)
    print(f"Found {len(elements)} elements for '{selector}'")
    return elements
```

### 타이밍 조정

```python
# 기본 딜레이 증가
TYPING_DELAY_MS = (100, 300)  # 기존: (50, 200)

# 요소 대기 시간 증가
page.wait_for_selector(".se-content", timeout=60000)  # 기존: 30000
```

---

## 주의사항

- 디버그 모드에서는 headless=False 필수
- 스크린샷은 민감 정보 마스킹 필요
- 콘솔 로그는 30분간만 보관
- 실패 3회 연속 시 수동 개입 요청

---

## 연계 에이전트

- **이전**: `pipeline-runner` (파이프라인 실행)
- **에러 해결**: `auto-error-resolver`
