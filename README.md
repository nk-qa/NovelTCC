# NovelTCC
Confluence 기획서 URL을 입력하면 QA 테스트케이스를 자동 설계하여 xlsx로 출력하는 도구입니다.

---

## 실행 방법

배포 폴더(`NovelTCC_V.x.x`) 안의 **`NovelTCC.exe`** 를 실행합니다.

> `_internal` 폴더, `sample.xlsx`, `gui` 폴더는 exe와 **같은 위치**에 있어야 합니다. 이동 시 폴더째 이동하세요.

---

## 초기 설정

처음 실행 후 우측 상단 **설정** 버튼을 눌러 아래 항목을 입력합니다.

### Confluence 설정

| 항목 | 입력값 |
|------|--------|
| Base URL | `https://su-nk.atlassian.net/` |
| 이메일 | Atlassian 로그인 이메일 |
| API Token | 아래 방법으로 발급 |

**API Token 발급 방법**
1. [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) 접속
2. **Create API token** 클릭 → 이름 입력 후 발급
3. 발급된 토큰을 복사하여 입력

### Claude 설정

| 연동 방식 | 조건 | 비고 |
|-----------|------|------|
| **Claude Code CLI** | Claude Code가 설치된 PC | 별도 API 비용 없음 |
| **API Key** | Anthropic API Key 보유 | [console.anthropic.com](https://console.anthropic.com) 에서 발급 |

설정 완료 후 각각 **연결 테스트 / CLI 확인 / 키 확인** 버튼으로 정상 여부를 확인하고 **저장**합니다.

---

## 사용 방법

1. 기획서 URL 입력란에 Confluence 페이지 URL 붙여넣기
2. **조회** 버튼으로 페이지 제목 확인
3. 출력 파일 경로 지정 (기본: 실행 폴더 내 `TC_Result.xlsx`)
4. **TC 생성 시작** 클릭
5. 완료 후 **파일 위치 열기** 버튼으로 결과물 확인

---

## TC 설계 지침 커스터마이징

`prompt.md` 파일을 텍스트 에디터로 열어 내용을 수정하면, 기본 TC 설계 원칙에 추가 지침을 덧붙일 수 있습니다.

```
# 예시
- 이 기능은 iOS / Android 크로스 플랫폼 동작을 반드시 확인할 것
- 네트워크 지연(3G 환경) 케이스를 포함할 것
```

---

## 문의

QA팀 내부 문의 또는 GitHub Issues 등록
