# MCP 서버

> 상태: backlog. 기존 2단계 안이다. 미룬 이유는 [backlog/](README.md)를 따른다.

MCP 서버를 도구 허브로 하나 두고, 디스코드 봇·Claude Desktop·Claude Code·CI가 같은 도구를 재사용한다. 서버 구성은 [hosting/](hosting/README.md)을 따른다.

## 도입 목적

- 도구를 한 번 만들어 디스코드 봇(Agent SDK)과 개발자 IDE가 함께 쓰고, 권한 제어도 한 곳에서 처리한다.
- Claude Code를 쓰지 않는 사람(디자이너 등)도 디스코드 봇이나 Claude Desktop으로 위키를 쓴다.

```text
[원본 자료]                 [수집]                [지식 저장소]
회의록(.md), 기획서   ──▶  Ingest 에이전트  ──▶  Wiki (git, 마크다운)
                           (PR로 수정안 생성,       │
                            사람이 승인)            │
                                                    ▼
                         ┌──────── MCP 서버 (도구 허브) ────────┐
                         │  search_wiki       read_page         │
                         │  list_decisions    search_decisions  │
                         │  read_decision     search_code       │
                         │  report_gap                          │
                         └──────────────────┬───────────────────┘
                   ┌─────────────┬──────────┴──────┬─────────────┐
              디스코드 봇    Claude Desktop    Claude Code    PR 리뷰 봇
              (전 인원)      (디자이너 등)     (개발자 IDE)    (CI)
```

## MCP 도구

| 도구 | 역할 |
| --- | --- |
| `search_wiki` | 위키 검색. 질의를 정규화한 뒤 경로·제목·요약 목록 반환 |
| `read_page` | 페이지 본문 읽기 |
| `list_decisions` | 도메인·플랫폼별 현재 유효한 결정 목록 |
| `search_decisions` | 결정 검색. 대체된 결정은 기본 제외 |
| `read_decision` | 결정 본문과 대체 이력 읽기 |
| `search_code` | 코드 레포 3개 grep 탐색 |
| `report_gap` | 답하지 못한 질문 기록([검색 고도화](search-upgrades.md#report_gap)) |

**결과 반환**

1. 경로, 제목, 요약(160자 이내) 목록을 최대 7건 돌려준다.
2. 필요한 페이지만 본문을 읽는다.

토큰을 아끼고, 답변에 붙일 출처를 고르기 쉽게 하기 위해서다. 대체된 결정의 처리는 [위키 조회](../retrieval.md#위키-조회)와 같다.

## 서버 지시문

MCP 서버에 아래 규칙을 지시문으로 넣어, 어느 클라이언트에서 쓰든 같은 방식으로 답하게 한다.

1. 업무 질문이면 먼저 `search_wiki`를 호출한다. 이전 검색 결과나 기억으로 대신하지 않는다.
2. 사용자 질문을 줄이지 않고 그대로 검색어로 넘긴다. 정규화는 서버가 한다([형태소 분석기 정규화](search-upgrades.md#형태소-분석기-정규화)).
3. "위키에 없다"고 답하기 전에 `search_decisions`로 한 번 더 찾는다. 그래도 없으면 `report_gap`을 호출한다.
4. 답변에 참조한 페이지, 원본 회의록, 날짜를 붙인다.

## 도입할 때 바뀌는 것

- 플러그인에 MCP 설정을 추가하고, ask 스킬이 로컬 clone 대신 MCP 도구를 쓴다. 코드 레포 쪽 `.claude/settings.json`은 바꾸지 않는다([설치와 배포](../plugin.md#설치와-배포)).
- 개인 토큰은 플러그인 설정에 넣지 않고 각자 환경 변수로 넣는다([외부 노출과 인증](hosting/security.md#외부-노출과-인증)).

## 미결 사항

- [ ] 디자이너의 Claude Desktop 연동이 필요한가? ([외부 노출과 인증](hosting/security.md#외부-노출과-인증)의 OAuth 구현 여부)
- [ ] 호스팅 서버 운영 담당자는 누구인가? (장애 대응)
- [ ] 구매할 도메인 이름
