# 보안

호스팅 서버의 외부 노출, 인증, 권한, 비밀값을 정한다. 네트워크 구성은 [infra.md](infra.md#네트워크)를 따른다.

## 외부 노출과 인증

| 클라이언트 | 접속 출발점 | 방식 |
| --- | --- | --- |
| 디스코드 봇 | 같은 서버 | `http://app:8080/mcp`, 서비스 토큰 |
| Claude Code (개발자) | 각자 PC | 터널 URL + 헤더 토큰 |
| Claude Desktop, claude.ai 커넥터 (디자이너) | Anthropic 클라우드 | 공인 HTTPS와 OAuth가 필요하다. 서버 도입 초반에는 붙이지 않는다 |

- 토큰은 사람별로 발급하고 sqlite에는 해시만 저장한다. 퇴사자는 그 토큰만 폐기하고, 검색 기록에 질문자가 남는다.
- 플러그인 MCP 설정에는 토큰을 넣지 않고 각자 환경 변수로 넣는다.
  ```json
  {
    "type": "http",
    "url": "https://wiki-mcp.<도메인>/mcp",
    "headers": { "Authorization": "Bearer ${GGUK_MCP_TOKEN}" }
  }
  ```
- 디자이너는 서버 도입 초반에 디스코드 봇을 쓴다. Desktop 연동은 수요가 확인되면 OAuth와 함께 붙인다.
- 봇은 GGUK 디스코드 서버와 지정한 역할에만 응답한다.

## 권한과 비밀값

**GitHub App 하나로 레포 권한을 모은다**

| 대상 | 권한 | 쓰는 곳 |
| --- | --- | --- |
| 코드 레포 3개 | Contents: Read | syncer |
| `gguk-wiki` | Contents: Write, Pull requests: Write | 봇(회의록 커밋, [반영] 버튼 merge), CI(인덱스 재생성 커밋), syncer |

- 이 App은 main 보호 규칙의 유일한 우회 대상이다([main 보호 규칙](../../ingest.md#main-보호-규칙)). 1단계에서는 CI의 인덱스 재생성만 이 App을 쓴다.
- 봇은 공유 clone에 쓰지 않고 GitHub API로 커밋한다. 그래서 app에는 clone 볼륨을 읽기 전용으로 붙인다.
- Installation 토큰은 1시간이면 만료되므로 앱 개인 키로 다시 발급받는다.

**Anthropic API 키**

- 위키 전용 workspace에서 발급하고 지출 한도를 건다.
- 서버(봇)용과 Actions(Ingest, lint)용 키를 나눈다.
- 여러 사람이 쓰는 봇이므로 개인 구독 로그인 대신 API 키를 쓴다.

**봇 에이전트의 도구를 MCP로 제한한다**

Agent SDK의 `allowed_tools`를 `mcp__gguk__*`로만 열고 Bash, Write, Read 같은 내장 도구는 끈다. 봇은 여러 사람의 입력과 회의록, 코드를 읽는다. 그 안의 프롬프트 인젝션이 서버 셸에 닿으면 안 된다.

**비밀값 위치**

| 이름 | 용도 | 위치 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | 봇 | Parameter Store |
| `DISCORD_BOT_TOKEN` | 봇 | Parameter Store |
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` | 봇, syncer | Parameter Store |
| `MCP_SERVICE_TOKEN` | 봇 → app | Parameter Store |
| `CF_TUNNEL_TOKEN` | cloudflared | Parameter Store |
| `ANTHROPIC_API_KEY` | Ingest, lint | GitHub Actions secrets |
| `DISCORD_WEBHOOK_URL` | Actions 알림 | GitHub Actions secrets |
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` | 인덱스 재생성 커밋 | GitHub Actions secrets |

AWS 키는 레포에 저장하지 않는다. Actions는 OIDC로 배포 역할을 받는다.
