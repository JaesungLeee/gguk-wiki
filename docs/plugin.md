# Claude Code 플러그인

1단계에서 팀원이 위키를 쓰는 방식을 정한다. 플러그인 하나로 위키 넣기, 위키 조회, 다른 레포 조회를 제공한다.

## 구성

| 스킬 | 역할 | 규칙 |
| --- | --- | --- |
| `ingest` | 위키에 정보 넣기 | [ingest.md](ingest.md) |
| `ask` | 위키와 코드 레포 조회 | [retrieval.md](retrieval.md) |

- `ask` 스킬 설명에 "GGUK의 정책, 결정, 다른 플랫폼 구현을 물을 때" 같은 사용 조건을 적는다. 사용자가 명령을 치지 않아도 Claude가 필요할 때 스스로 부르게 하기 위해서다.
- 훅과 자체 MCP 서버 설정은 넣지 않는다([훅](backlog/hooks.md), [MCP 서버](backlog/mcp-server.md)).
- 노션 MCP도 플러그인에 넣지 않는다. 넣으면 노션을 쓰지 않는 팀원에게도 인증 안내가 뜬다. 필요한 사람만 직접 추가한다([필요 조건](#필요-조건)).
- 스킬은 SKILL.md 형식으로 쓴다([다른 LLM 도구 지원](#다른-llm-도구-지원-1단계-확장)).

**절차는 `AGENTS.md`에 둔다**

ingest와 조회 절차는 위키 레포의 `AGENTS.md`에만 적고, 두 스킬의 SKILL.md는 동적 주입으로 그 파일을 읽어 들인다. 스킬은 주로 코드 레포에서 불리는데, 그때 위키 레포의 `AGENTS.md`는 자동으로 읽히지 않기 때문이다.

```markdown
---
name: ask
description: GGUK의 정책, 결정, 다른 플랫폼 구현을 물을 때
---
!`git -C "${GGUK_HOME:-$HOME/gguk}/gguk-wiki" show origin/HEAD:AGENTS.md`
```

- `` !`명령` ``은 스킬 내용이 Claude에게 전달되기 전에 실행되고, 출력이 그 자리에 들어간다([Claude Code 스킬 문서](https://code.claude.com/docs/en/skills)). Claude가 읽을지 판단하지 않으므로 항상 들어간다.
- 작업 폴더가 아니라 `origin/HEAD`를 읽는다([읽는 기준](retrieval.md#읽는-기준)). 위키 clone이 ingest 작업 브랜치에 있어도 영향이 없다.
- clone이 없으면 오류 문구가 들어가므로, SKILL.md 본문에서 설정 스크립트 실행을 안내한다.
- Windows(Git Bash)에서 동작하는지는 플러그인을 만들 때 확인한다.

## 설치와 배포

- `gguk-wiki` 레포를 Claude Code 플러그인 마켓플레이스로 쓴다. 플러그인은 `plugin/`에 둔다.
- 코드 레포 3곳과 위키 레포의 `.claude/settings.json`에 마켓플레이스(`extraKnownMarketplaces`)와 플러그인(`enabledPlugins`)만 등록한다. 레포를 처음 연 팀원에게 설치가 안내된다.
- 등록은 각 팀원이 그 폴더를 신뢰(trust)한 뒤에 적용된다.
- 위키 레포가 public이라 인증 없이 설치된다.

```json
{
  "extraKnownMarketplaces": {
    "gguk": { "source": { "source": "github", "repo": "JaesungLeee/gguk-wiki" } }
  },
  "enabledPlugins": { "gguk-wiki@gguk": true }
}
```

## 작업 공간

ingest와 ask 스킬이 레포 위치를 묻지 않도록, 레포 4개를 정해진 폴더 하나 아래에 둔다.

```text
~/gguk/                  # GGUK_HOME. 바꾸려면 환경 변수 GGUK_HOME을 설정한다
├── gguk-wiki/
├── Team-MINO-Node/
├── Team-MINO-Android/
└── Team-MINO-iOS/
```

- 작업용 clone이 따로 있어도 여기에 별도로 clone한다. 세 레포를 합쳐 약 64MB라 부담이 작고, 링크로 재사용하면 Windows에서 동작이 달라진다(Git Bash의 `ln -s`는 기본 설정에서 복사본을 만든다).
- ingest와 ask는 같은 위키 clone을 쓴다. ingest는 이 clone에서 작업 브랜치를 만들지만, ask는 `origin/HEAD`를 읽으므로 영향을 받지 않는다([읽는 기준](retrieval.md#읽는-기준)).
- 레포가 없으면 두 스킬 모두 설정 스크립트 실행을 안내한다.

**설정 스크립트 `scripts/setup-workspace.sh`**

처음에 한 번 실행한다. Windows에서는 Git Bash에서 실행한다.

```bash
git clone https://github.com/JaesungLeee/gguk-wiki.git ~/gguk/gguk-wiki
~/gguk/gguk-wiki/scripts/setup-workspace.sh
```

1. `git`이 설치되어 있는지 확인한다. `gh`가 없거나 `gh auth status`로 로그인되어 있지 않으면 "조회는 쓸 수 있고, ingest는 `gh auth login` 후 쓸 수 있다"고 알리고 계속한다. 레포가 모두 public이라 clone에는 로그인이 필요 없다.
2. 코드 레포 3개를 하나씩 처리한다. 이미 있으면 건너뛰고, 없으면 clone한다. Windows에서는 `core.longpaths=true`를 설정한다.
3. 실패한 레포는 이유를 알려 주고 나머지를 계속 진행한다.
4. 레포별 준비 상태를 요약해 보여 준다.

- 여러 번 실행해도 결과가 같다. 레포가 추가되면 다시 실행한다.
- 개발자 PC에 Python 설치를 요구하지 않도록 bash로 쓴다.

## 필요 조건

| 항목 | 내용 |
| --- | --- |
| Claude Code | Pro 이상 구독. Free 플랜은 Claude Code를 쓸 수 없다 |
| git | Windows는 Git for Windows 또는 WSL이 필요하다. Git for Windows가 있으면 Claude Code의 Bash 도구가 Git Bash로 실행되어, macOS와 같은 명령이 동작한다 |
| gh | 로그인이 필요하다(`gh auth login`). ingest 스킬이 PR을 만들 때 쓴다. 조회만 하면 필요 없다 |
| 위키 레포 write 권한 | 협업자로 초대받아야 한다. 조회만 하면 필요 없다 |
| 노션 MCP (선택) | 노션 회의록을 MCP로 넣는 사람만 필요하다. `claude mcp add --transport http notion https://mcp.notion.com/mcp`로 추가한 뒤 `/mcp`에서 OAuth로 인증한다. 노션 워크스페이스 멤버여야 하고, 게스트는 연결할 수 없다 |

노션 MCP의 서버 이름은 `notion`으로 맞춘다. ingest 스킬은 `notion-search`, `notion-fetch`만 허용 도구로 적는다. 다른 노션 도구는 Claude Code가 실행 전에 허락을 묻는다.

## 다른 LLM 도구 지원 (1단계 확장)

Claude Code가 아닌 LLM 도구를 쓰는 팀원도 같은 위키를 쓰게 한다. 처음부터 다른 도구도 읽을 수 있는 형식으로 써 두고, 배포는 확장 단계에서 정한다.

- 위키 운영 규칙은 `AGENTS.md`에 둔다. Codex, Gemini CLI, Cursor, GitHub Copilot 등이 읽는 파일이다.
- `CLAUDE.md`에는 `@AGENTS.md` 한 줄만 둔다. Claude Code는 `CLAUDE.md`가 있으면 `AGENTS.md`를 따로 읽지 않으므로 import로 연결한다.
- 스킬은 공개 형식인 SKILL.md로 쓴다. Codex와 Gemini CLI도 이 형식을 읽지만, 도구마다 읽는 폴더가 다르다(Codex는 `.agents/skills/`, Claude Code는 플러그인이나 `.claude/skills/`).
- SKILL.md의 `` !`명령` `` 주입은 Claude Code 전용이다. 다른 도구용 스킬에는 "먼저 `git -C ~/gguk/gguk-wiki show origin/HEAD:AGENTS.md`를 실행해 읽고 따른다"는 지시문을 적는다([절차는 AGENTS.md에 둔다](#구성)).
- 설정 스크립트는 bash다. PowerShell만 쓰는 도구가 있으면 PowerShell 판을 검토한다.

**지원 기준**: `AGENTS.md`를 읽고 셸 명령(`git`, `gh`)을 실행할 수 있는 에이전트형 도구면 지원 대상으로 본다. 팀원별 도구는 조사하지 않는다.

- 동작 검증은 Claude Code만 한다. 다른 도구는 쓰는 팀원이 나오면 그 도구로 확인하고, 그 도구가 읽는 폴더에 스킬을 추가한다.
- 웹 채팅 전용 도구(ChatGPT, Gemini, Claude 웹앱 등)는 로컬 clone을 읽거나 `gh`를 실행할 수 없어 지원하지 않는다. 지원하려면 [MCP 서버](backlog/mcp-server.md)가 필요하다.
- 에이전트형 도구를 쓸 수 없는 팀원은 설치 안내 때 직접 알린다. 무료 플랜으로는 쓸 수 없는 도구가 있다. 예: Claude Free 플랜은 Claude Code를 쓸 수 없다([필요 조건](#필요-조건)).
