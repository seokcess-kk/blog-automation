# Scrapling Guidelines

> **enforcement: suggest**
> Scrapling 라이브러리 사용 가이드라인 (읽기 전용 크롤링)

---

## 1. 핵심 원칙

```
Scrapling = 읽기 전용 (크롤링, 데이터 수집)
Playwright = 쓰기 작업 (에디터 조작, 발행)
```

**두 라이브러리의 역할을 절대 혼용하지 말 것.**

---

## 2. StealthyFetcher 사용법

### 2.1 기본 설정

```python
from scrapling import StealthyFetcher

fetcher = StealthyFetcher(
    headless=True,
    network_idle=True,
    block_images=False,  # 이미지 분석 필요 시 False
    disable_resources=False,
)
```

### 2.2 페이지 가져오기

```python
# 기본 fetch
page = fetcher.fetch(url)

# 타임아웃 설정
page = fetcher.fetch(url, timeout=30000)

# 특정 셀렉터 대기
page = fetcher.fetch(url, wait_selector=".blog-content")
```

### 2.3 Adaptor 활용 (자동 셀렉터 탐지)

```python
# Adaptive 셀렉터 - 구조 변경에 강함
content = page.css_first(".se-main-container")

# 여러 요소 선택
images = page.css("img.se-image")

# 텍스트 추출
text = page.css_first(".se-text").text

# 속성 추출
src = page.css_first("img").attrib.get("src")
```

---

## 3. 네이버 블로그 크롤링 패턴

### 3.1 상위노출 블로그 URL 수집

```python
async def collect_serp_urls(keyword: str, count: int = 5) -> list[str]:
    """네이버 검색 결과에서 상위 블로그 URL 수집"""
    search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}"
    page = fetcher.fetch(search_url)

    # 블로그 링크 추출
    links = page.css("a.api_txt_lines.total_tit")
    urls = [link.attrib.get("href") for link in links[:count]]

    return urls
```

### 3.2 블로그 본문 파싱

```python
def parse_blog_content(url: str) -> dict:
    """블로그 본문 구조 분석"""
    page = fetcher.fetch(url, wait_selector=".se-main-container")

    # 스마트에디터 컨테이너
    container = page.css_first(".se-main-container")

    return {
        "title": page.css_first(".se-title-text").text,
        "char_count": len(container.text),
        "image_count": len(page.css("img.se-image")),
        "headings": [h.text for h in page.css(".se-section-text h2, .se-section-text h3")],
        "paragraphs": [p.text for p in page.css(".se-text-paragraph")],
    }
```

---

## 4. 에러 처리

### 4.1 재시도 패턴

```python
import asyncio
from typing import Optional

async def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_base: float = 2.0
) -> Optional[Page]:
    """지수 백오프 재시도"""
    for attempt in range(max_retries):
        try:
            return fetcher.fetch(url, timeout=30000)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff_base ** attempt
            await asyncio.sleep(wait_time)
    return None
```

### 4.2 일반적인 에러

| 에러 | 원인 | 해결책 |
|------|------|--------|
| TimeoutError | 페이지 로딩 지연 | timeout 증가, wait_selector 확인 |
| ElementNotFound | 셀렉터 불일치 | Adaptive 셀렉터 사용 |
| ConnectionError | 네트워크 문제 | 재시도 로직 적용 |
| BlockedError | 봇 탐지 | headless=False 테스트 |

---

## 5. 성능 최적화

### 5.1 리소스 절약

```python
# 불필요한 리소스 차단
fetcher = StealthyFetcher(
    block_images=True,      # 이미지 불필요 시
    disable_resources=True, # CSS/폰트 차단
)
```

### 5.2 병렬 처리

```python
import asyncio

async def collect_patterns(urls: list[str]) -> list[dict]:
    """여러 URL 병렬 크롤링"""
    tasks = [parse_blog_content(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 에러 필터링
    return [r for r in results if not isinstance(r, Exception)]
```

---

## 6. 주의사항

### 6.1 절대 하지 말 것

- Scrapling으로 form 제출 시도
- Scrapling으로 로그인 처리 시도
- Scrapling으로 에디터 조작 시도

→ **위 작업은 반드시 Playwright 사용**

### 6.2 크롤링 예절

- 요청 간격: 최소 1초 이상
- User-Agent: 기본값 사용 (StealthyFetcher가 자동 처리)
- robots.txt: 가급적 준수

### 6.3 셀렉터 유지보수

네이버 UI 변경 시 셀렉터 업데이트 필요:
- `.se-main-container`: 스마트에디터 본문
- `.se-text-paragraph`: 텍스트 단락
- `.se-image`: 이미지

---

## 7. 참고 자료

- [Scrapling 공식 문서](https://github.com/D4Vinci/Scrapling)
- [네이버 스마트에디터 구조 분석](./resources/naver-editor-structure.md)
