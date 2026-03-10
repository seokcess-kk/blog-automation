# 네이버 스마트에디터 구조

> 네이버 블로그 스마트에디터 3.0 (SE3) 기준

---

## 1. 페이지 구조

### 1.1 URL 패턴

```
글쓰기: https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}
수정:   https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}&logNo={log_no}
발행됨: https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}
```

### 1.2 iframe 구조

```
page
└── iframe#mainFrame           ← 메인 컨텐츠
    └── div.se-content         ← 에디터 영역
        ├── div.se-title       ← 제목 영역
        └── div.se-body        ← 본문 영역
```

**중요:** 모든 에디터 조작은 `mainFrame` 내에서 수행해야 함.

---

## 2. 주요 셀렉터

### 2.1 에디터 영역

| 요소 | 셀렉터 | 용도 |
|------|--------|------|
| 메인 프레임 | `iframe#mainFrame` | iframe 진입 |
| 에디터 컨테이너 | `.se-content` | 에디터 전체 |
| 제목 입력 | `.se-title-text` | 제목 타이핑 |
| 본문 컨테이너 | `.se-body` | 본문 영역 |
| 텍스트 단락 | `.se-text-paragraph` | 텍스트 입력 |

### 2.2 툴바

| 요소 | 셀렉터 | 용도 |
|------|--------|------|
| 이미지 버튼 | `.se-image-toolbar-button` | 이미지 삽입 |
| 동영상 버튼 | `.se-video-toolbar-button` | 동영상 삽입 |
| 구분선 버튼 | `.se-hr-toolbar-button` | 구분선 삽입 |
| 인용구 버튼 | `.se-quote-toolbar-button` | 인용구 삽입 |
| 링크 버튼 | `.se-link-toolbar-button` | 링크 삽입 |

### 2.3 이미지 업로드

| 요소 | 셀렉터 | 용도 |
|------|--------|------|
| 업로드 버튼 | `.se-upload-button` | 파일 선택 |
| 업로드된 이미지 | `.se-image-resource` | 업로드 완료 확인 |
| 이미지 설명 | `.se-image-caption` | 대체 텍스트 |

### 2.4 태그/카테고리

| 요소 | 셀렉터 | 용도 |
|------|--------|------|
| 태그 입력 | `.tag_post_area input` | 태그 타이핑 |
| 카테고리 선택 | `.category_select` | 카테고리 드롭다운 |
| 공개 설정 | `.open_type_select` | 공개/비공개 |

### 2.5 발행

| 요소 | 셀렉터 | 용도 |
|------|--------|------|
| 발행 버튼 | `.publish_btn` | 발행 시작 |
| 확인 버튼 | `.confirm_btn` | 발행 확인 |
| 임시저장 | `.temp_save_btn` | 임시저장 |

---

## 3. 에디터 조작 시퀀스

### 3.1 글 작성 전체 흐름

```
1. PostWriteForm.naver 접속
2. mainFrame 대기 (wait_for_selector)
3. mainFrame 진입 (page.frame())
4. .se-content 대기
5. 제목 입력 (.se-title-text)
6. 본문 입력 (.se-text-paragraph)
7. 이미지 삽입 (반복)
8. 태그 입력
9. 발행 버튼 클릭
10. 확인 버튼 클릭
11. PostView.naver URL 확인
```

### 3.2 iframe 진입 코드

```python
def get_editor_frame(page):
    """에디터 iframe 가져오기"""
    page.wait_for_selector("iframe#mainFrame", timeout=10000)
    frame = page.frame("mainFrame")
    frame.wait_for_selector(".se-content", timeout=10000)
    return frame
```

---

## 4. 주의사항

### 4.1 타이밍 이슈

- iframe 로딩 후 `.se-content` 대기 필수
- 이미지 업로드 후 `.se-image-resource` 대기 필수
- 발행 버튼 클릭 후 URL 변경 대기 필수

### 4.2 셀렉터 변경 대응

네이버 UI 업데이트 시 셀렉터가 변경될 수 있음:

```python
# 셀렉터 상수화
SELECTORS = {
    "main_frame": "iframe#mainFrame",
    "editor": ".se-content",
    "title": ".se-title-text",
    "paragraph": ".se-text-paragraph",
    "image_btn": ".se-image-toolbar-button",
    "publish_btn": ".publish_btn",
}

# 셀렉터 오류 시 이 파일 업데이트
```

### 4.3 에러 복구

| 상황 | 대응 |
|------|------|
| iframe 로딩 실패 | 페이지 새로고침 후 재시도 |
| 요소 클릭 실패 | JavaScript 클릭 시도 |
| 업로드 실패 | 이미지 크기/형식 확인 |
| 발행 실패 | 스크린샷 저장 후 로깅 |

---

## 5. 디버깅

### 5.1 스크린샷 저장

```python
def debug_screenshot(page, name: str):
    """디버깅용 스크린샷"""
    page.screenshot(path=f"debug/{name}_{int(time.time())}.png")
```

### 5.2 콘솔 로그 캡처

```python
page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
```

---

## 6. 버전 히스토리

| 날짜 | 변경사항 |
|------|----------|
| 2025-03 | 초기 문서 작성 (SE3 기준) |
