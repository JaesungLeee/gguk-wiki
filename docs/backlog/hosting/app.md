# 앱

서버에서 돌아가는 코드의 언어, 구조, 저장소를 정한다.

## 구현 스택

봇, MCP 서버, syncer, 위키 레포의 `scripts/`, 검색 평가 실행기를 모두 Python으로 쓴다.

| 용도 | 선택 |
| --- | --- |
| 런타임, 패키지 | Python 3.12+, uv |
| HTTP 서버 | FastAPI + uvicorn |
| MCP | 공식 `mcp` SDK의 FastMCP. FastAPI에 mount한다 |
| 디스코드 봇 | discord.py + claude-agent-sdk |
| 한국어 정규화 | kiwipiepy (Kiwi 형태소 분석기) |
| 검색 | ripgrep 호출 |
| 저장 | sqlite3 |
| frontmatter | PyYAML, python-frontmatter |
| 품질 | pytest, ruff |

**Python을 고른 이유**

- 서버 쪽 질의 정규화에 Kiwi 형태소 분석기를 쓴다([형태소 분석기 정규화](../search-upgrades.md#형태소-분석기-정규화)).
- 평가셋 비교, 하이브리드 검색(sqlite-vec, 임베딩)처럼 예정된 확장이 Python 쪽이 유리하다.
- Kotlin은 팀에 가장 익숙하지만 Agent SDK가 없어 제외했다. TypeScript도 가능하지만 한국어 처리 때문에 Python을 택했다. 운영 인력이 적으므로 봇과 서버를 다른 언어로 나누지 않는다.

**예외: 개발자 PC에서 도는 코드는 bash로 쓴다**

Claude Code 훅([hooks.md](../hooks.md))과 [설정 스크립트](../../plugin.md#작업-공간)는 개발자 PC에서 실행되므로 Python 버전이나 패키지에 의존하지 않는다.

## 앱 구조

app 컨테이너는 FastAPI 앱 하나이고, MCP를 그 안에 mount한다. 봇은 별도 프로세스로 두며 HTTP 서버를 갖지 않는다.

| 경로 | 용도 | 인증 |
| --- | --- | --- |
| `/mcp` | [MCP 도구](../mcp-server.md#mcp-도구) | 사람별 토큰 |
| `/hooks/session-start` | 세션 시작 훅용 결정 요약 | 사람별 토큰 |
| `/hooks/prompt-search` | 프롬프트 입력 훅용 검색 (선택) | 사람별 토큰 |
| `/webhooks/github` | push 웹훅 (polling을 대체할 때) | GitHub 서명 검증 |
| `/health` | 업타임 체크 | 없음 |

토큰 발급과 관리는 [security.md](security.md#외부-노출과-인증)를 따른다.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gguk", stateless_http=True, streamable_http_path="/")

@mcp.tool()
def search_wiki(query: str) -> list[dict]: ...

mcp_app = mcp.streamable_http_app()  # session_manager가 이 호출에서 만들어진다

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp_app)

@app.get("/hooks/session-start")
def session_start(platform: Platform): ...
```

**구현 주의**

- `session_manager.run()`을 FastAPI lifespan에 연결한다. 빠뜨리면 첫 MCP 요청에서 task group 초기화 오류가 난다.
- FastMCP 기본 경로가 `/mcp`라서 `/mcp`에 mount하면 `/mcp/mcp`가 된다. `streamable_http_path="/"`로 바꾼다.
- FastAPI `Depends`는 mount한 하위 앱에 적용되지 않는다. 토큰 검사는 ASGI 미들웨어로 앱 전체에 걸고 `/health`만 뺀다.
- `stateless_http=True`로 세션 상태를 두지 않는다. 배포로 재시작해도 Claude Code 연결이 깨지지 않는다.
- 별도 패키지 `fastmcp`(v2)의 FastAPI 라우트 자동 변환은 쓰지 않는다. 도구는 LLM이 쓰기 좋게 따로 설계한다.

## 저장소 구조

서버 코드는 별도 레포 `gguk-wiki-server`에 둔다. 위키 레포는 문서 PR과 플러그인 배포를 맡으므로 리뷰어와 CI를 섞지 않는다.

```text
gguk-wiki-server/
├── app/                # FastAPI + MCP 서버
├── bot/                # 디스코드 봇 + Agent SDK
├── syncer/             # git fetch 루프
├── evals/              # 평가 실행기. 평가셋은 위키 레포의 evals/search.jsonl을 읽는다
├── deploy/
│   ├── compose.yaml
│   ├── bootstrap.sh    # 빈 EC2 → 실행 가능한 상태까지
│   └── render-env.sh   # Parameter Store → .env
├── tests/
└── .github/workflows/deploy.yml
```

```yaml
# deploy/compose.yaml (초안)
services:
  app:
    image: ${ECR}/gguk-app:${TAG}
    env_file: .env
    volumes: [repos:/srv/repos:ro, data:/srv/data]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
    restart: unless-stopped
  bot:
    image: ${ECR}/gguk-bot:${TAG}
    env_file: .env
    environment: { MCP_URL: "http://app:8080/mcp" }
    depends_on: [app]
    restart: unless-stopped
  syncer:
    image: ${ECR}/gguk-syncer:${TAG}
    env_file: .env
    volumes: [repos:/srv/repos]
    restart: unless-stopped
  cloudflared:
    image: cloudflare/cloudflared:<고정 버전>
    command: tunnel run
    environment: { TUNNEL_TOKEN: "${CF_TUNNEL_TOKEN}" }
    restart: unless-stopped
volumes: { repos: {}, data: {} }
```

`TAG`는 배포 때 커밋 SHA로 넘긴다([배포](deploy.md#배포)). 로그 크기 제한은 `/etc/docker/daemon.json`에 한 번만 설정한다.
