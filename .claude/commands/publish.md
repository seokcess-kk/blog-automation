# /publish

> 블로그 발행 명령어

---

## 설명

생성된 원고를 네이버 블로그에 자동 발행합니다.

---

## 사용법

```
/publish <draft-id> [옵션]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--mode` | conservative | 발행 모드 |
| `--dry-run` | false | 테스트 모드 (실제 발행 안 함) |
| `--debug` | false | 디버그 모드 (스크린샷 저장) |

### 발행 모드

| 모드 | 일일 한도 | 최소 간격 | 주말 |
|------|-----------|-----------|------|
| conservative | 2개 | 4시간 | ❌ |
| normal | 4개 | 3시간 | ✅ |
| aggressive | 5개 | 2시간 | ✅ |

---

## 실행 내용

1. **사전 검증**
   - 발행 한도 체크
   - 발행 간격 체크
   - 발행 시간대 체크 (09:00~18:00)

2. **세션 확인**
   - user_data_dir 로드
   - 로그인 상태 확인
   - 필요시 재로그인

3. **에디터 조작** (Playwright)
   - mainFrame 진입
   - 제목 입력 (human_typing)
   - 본문 입력 (단락별 타이핑)
   - 이미지 업로드
   - 태그 입력

4. **발행**
   - 발행 버튼 클릭
   - 발행 완료 대기
   - URL 수집

5. **결과 저장**
   - drafts.status = 'published'
   - drafts.naver_post_url 저장
   - publish_logs 기록

---

## 출력 예시

```json
{
  "draft_id": "uuid-xxx",
  "status": "published",
  "naver_post_url": "https://blog.naver.com/blogid/123456789",
  "published_at": "2025-03-10T14:30:00+09:00",
  "duration_seconds": 180,
  "mode": "conservative"
}
```

---

## 관련 모듈

- `src/publisher/auth.py`
- `src/publisher/editor.py`
- `src/publisher/stealth.py`
- `src/publisher/scheduler.py`

---

## 주의사항

- **Playwright 전용** (Scrapling 사용 금지)
- 하루 5개 초과 발행 금지
- 의료 키워드는 conservative 모드 필수
- headless=False 권장 (봇 탐지 우회)
- 실패 시 자동 재시도 (max 3회)

---

## 에러 처리

| 에러 | 대응 |
|------|------|
| 로그인 실패 | 수동 재로그인 후 재시도 |
| 에디터 로딩 실패 | 타임아웃 증가 후 재시도 |
| 이미지 업로드 실패 | 이미지 크기 확인 후 재시도 |
| 발행 실패 | debug-publisher 에이전트 호출 |
