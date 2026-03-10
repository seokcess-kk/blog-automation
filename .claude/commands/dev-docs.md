# /dev-docs

> 개발 문서 생성 및 관리 명령어

---

## 설명

프로젝트의 개발 문서를 자동 생성하거나 업데이트합니다.

---

## 사용법

```
/dev-docs [옵션]
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `sync` | SPEC.md와 CLAUDE.md 동기화 |
| `api` | API 문서 생성 (src/ 기반) |
| `changelog` | 변경 이력 생성 |
| `all` | 모든 문서 생성/업데이트 |

---

## 실행 내용

### /dev-docs sync

1. SPEC.md 읽기
2. CLAUDE.md 현재 상태 확인
3. 변경 사항 식별
4. CLAUDE.md 업데이트
5. 변경 요약 출력

### /dev-docs api

1. src/ 디렉토리 스캔
2. 각 모듈의 docstring 추출
3. 함수/클래스 시그니처 수집
4. API 문서 생성 (docs/api.md)

### /dev-docs changelog

1. git log 분석
2. 커밋 메시지 파싱
3. 변경 유형별 분류 (feat, fix, refactor)
4. CHANGELOG.md 업데이트

---

## 출력 예시

```markdown
# 문서 동기화 완료

## 변경 사항
- CLAUDE.md: 기술 스택 버전 업데이트
- CLAUDE.md: 새로운 모듈 추가 (image_generator.py)

## 생성된 파일
- docs/api.md (2.5KB)
- CHANGELOG.md (업데이트)

## 다음 단계
- [ ] 변경 사항 검토
- [ ] git commit
```

---

## 관련 파일

- `SPEC.md`: 프로젝트 명세
- `CLAUDE.md`: 프로젝트 메모리
- `docs/api.md`: API 문서
- `CHANGELOG.md`: 변경 이력
