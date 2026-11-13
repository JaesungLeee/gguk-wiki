# Claude Code 플러그인

1단계에서 팀원이 위키를 쓰는 방식을 정한다. 플러그인 하나로 위키 넣기, 위키 조회, 다른 레포 조회를 제공한다.

## 구성

| 스킬 | 역할 | 규칙 |
| --- | --- | --- |
| `ingest` | 위키에 정보 넣기 | [procedures/ingest.md](../procedures/ingest.md) (이유: [ingest.md](ingest.md)) |
| `ask` | 위키와 코드 레포 조회 | [procedures/ask.md](../procedures/ask.md) (이유: [retrieval.md](retrieval.md)) |

- `ask` 스킬 설명에 "GGUK의 정책, 결정, 다른 플랫폼 구현을 물을 때" 같은 사용 조건을 적는다. 사용자가 명령을 치지 않아도 Claude가 필요할 때 스스로 부르게 하기 위해서다.
- 훅과 자체 MCP 서버 설정은 넣지 않는다([훅](backlog/hooks.md), [MCP 서버](backlog/mcp-server.md)).
- 노션 MCP도 플러그인에 넣지 않는다. 넣으면 노션을 쓰지 않는 팀원에게도 인증 안내가 뜬다. 필요한 사람만 직접 추가한다([필요 조건](#필요-조건)).
- 스킬은 SKILL.md 형식으로 쓴다([다른 LLM 도구 지원](#다른-llm-도구-지원-1단계-확장)).

**절차는 `AGENTS.md`에 둔다**

ingest와 조회 규칙은 위키 레포의 `AGENTS.md`(공통)와 `procedures/`(스킬별)에만 적고, 두 스킬의 SKILL.md는 동적 주입으로 그 파일들을 읽어 들인다. 스킬은 주로 코드 레포에서 불리는데, 그때 위키 레포의 파일은 자동으로 읽히지 않기 때문이다.

| 스킬 | 주입하는 파일 |
| --- | --- |
| `ask` | `AGENTS.md`, `procedures/ask.md` |
| `ingest` | `AGENTS.md`, `procedures/ingest.md`, `domains.yml`, `templates/` 4개(결정, 액션 아이템, 미결, 채팅 원본) |

```markdown
---
name: ask
description: GGUK의 정책, 결정, 다른 플랫폼 구현을 물을 때 쓴다
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh *)
---
!`"${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh" AGENTS.md procedures/ask.md`
```

- `` !`명령` ``은 스킬 내용이 Claude에게 전달되기 전에 실행되고, 출력이 그 자리에 들어간다([Claude Code 스킬 문서](https://code.claude.com/docs/en/skills)). Claude가 읽을지 판단하지 않으므로 항상 들어간다.
- 주입 명령은 플러그인의 [`scripts/wiki-show.sh`](../plugin/scripts/wiki-show.sh)를 부르고, 작업 공간 위치는 스크립트 안에서 정한다([작업 공간](#작업-공간)). `` !`명령` ``은 실행 전에 권한 규칙으로 검사되는데, 셸 변수(`$GGUK_HOME`, `${GGUK_HOME:-…}`)가 든 명령은 `allowed-tools`에 어떤 패턴을 적어도 "실행 전에 검사할 수 없다"며 스킬 호출이 중단된다. auto 모드에서만 통과한다. `${CLAUDE_PLUGIN_ROOT}`는 Claude Code가 검사 전에 실제 경로로 바꾸므로 통과한다(2026-11-13 확인).
- 스크립트는 읽기 전에 위키 clone을 fetch한다. 마지막 fetch 뒤에 바뀐 규칙도 바로 주입하기 위해서다. 약 0.5초 걸리고, 실패하면(오프라인) 마지막으로 받은 상태를 읽는다. 주입 맨 위에 기준 커밋과 fetch 결과를 표시한다.
- 규칙을 스킬별로 나눈 것은 주입량을 줄이기 위해서다. 한 파일(약 10,400자)일 때 ask는 필요 없는 ingest 규칙까지 받았다. 나눈 뒤 ask는 약 3,700자, ingest는 템플릿을 포함해 약 10,400자, 위키 레포 세션(`CLAUDE.md`)은 약 1,600자를 읽는다(2026-11-12 기준).
- ask는 `domains.yml`을 주입하지 않는다. 조회 1단계가 읽는 `wiki/index.md`에 도메인 이름과 범위가 있다.
- 상황에 맞는 파일만 LLM이 골라 읽게 하는 안은 제외했다. 읽지 않고 넘어가면 규칙이 빠지고, STT 공유 URL처럼 한 번 올라가면 되돌릴 수 없는 실수가 생긴다.
- Claude Code의 `.claude/rules/`는 쓰지 않는다. `paths`가 없는 규칙은 그 레포 세션마다 로드되고, `paths`가 있는 규칙은 Claude가 일치하는 파일을 읽을 때만 로드된다([Claude Code 메모리 문서](https://code.claude.com/docs/en/memory)). 코드 레포에서 부른 스킬에는 적용되지 않고, 작업 폴더를 읽으며, 다른 LLM 도구는 읽지 못한다. 같은 문서도 여러 단계로 된 절차는 skill로 옮기라고 안내한다.
- 규칙을 SKILL.md 본문에 직접 쓰지 않는 것은, 플러그인을 업데이트해야 바뀌어 팀원마다 다른 규칙을 쓸 수 있기 때문이다.
- 작업 폴더가 아니라 `origin/HEAD`를 읽는다([읽는 기준](retrieval.md#읽는-기준)). 위키 clone이 ingest 작업 브랜치에 있어도 영향이 없다.
- 주입 명령이 0이 아닌 코드로 끝나면 Claude Code는 스킬 호출을 중단하고 명령의 오류만 보여 준다. SKILL.md 본문의 안내도 전달되지 않는다(2026-11-13 확인). 그래서 스크립트는 clone, `origin/HEAD`, 규칙 파일이 없을 때 `[GGUK 위키 규칙을 읽지 못함]`과 해결 방법(설정 스크립트 실행 등)을 출력하고 0으로 끝낸다. SKILL.md 본문은 이 줄을 보면 안내만 전하고 멈추게 한다.
- Windows(Git Bash)에서 동작하는지는 아직 확인하지 못했다. macOS에서만 확인했다(2026-11-13).

**허용 도구**

스킬이 실행 중일 때 묻지 않고 허용하는 도구(`allowed-tools`)는 아래만 적는다.

| 스킬 | 허용 도구 |
| --- | --- |
| `ask` | 주입 스크립트, `git -C <레포>`의 `fetch`, `remote set-head`, `grep`, `show`, `log`, `rev-parse`, `ls-tree` |
| `ingest` | 주입 스크립트, 노션 MCP의 `notion-search`, `notion-fetch` |

- 주입 스크립트는 허용하지 않으면 스킬 호출이 중단된다(auto 모드 제외).
- ask의 git 읽기 명령은 허용하지 않으면 default 모드에서 매번 허락을 묻는다(2026-11-13 확인). 조회 한 번에 여러 번 묻지 않도록 허용한다. `checkout`, `push` 같은 쓰기 명령은 허용하지 않는다.
- ingest의 브랜치 생성, 커밋, `gh pr create`는 허용하지 않는다. 업로더가 실행마다 확인한다.

## 설치와 배포

사용법: [README.md 플러그인 설치](../README.md#플러그인-설치)

- `gguk-wiki` 레포를 Claude Code 플러그인 마켓플레이스로 쓴다. 마켓플레이스 정의는 `.claude-plugin/marketplace.json`, 플러그인은 `plugin/`에 둔다.
- 팀원은 각자 사용자 범위(`--scope user`)로 한 번 설치한다. 코드 레포 3곳과 위키 레포 어디서든 스킬을 부를 수 있다.
- 코드 레포 3곳과 위키 레포의 `.claude/settings.json`에 마켓플레이스(`extraKnownMarketplaces`)와 플러그인(`enabledPlugins`)만 등록한다. 폴더를 신뢰(trust)한 팀원에게 마켓플레이스가 등록되고 자동 업데이트가 켜진다.
- 등록만으로는 플러그인이 설치되지 않는다. project 설정에서 켠 플러그인도 각자 설치해야 로드된다([Claude Code 플러그인 로딩 문서](https://code.claude.com/docs/en/plugins/loading.md#enabled-in-project-settings-but-not-installed)).
- 위키 레포가 public이라 인증 없이 설치된다. GitHub SSH 키가 없으면 `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`을 설정한다. 셸의 `claude plugin` 명령은 SSH 확인이 실패하면 HTTPS로 바꿔 clone하지만(2026-11-13 확인), 세션 안 `/plugin` 설치와 플러그인 업데이트는 바꾸지 않아 실패한다([마켓플레이스 운영 문서](https://code.claude.com/docs/en/plugins/host-marketplace.md#serve-users-who-have-no-git-host-account)).

```json
{
  "extraKnownMarketplaces": {
    "gguk": {
      "source": { "source": "github", "repo": "JaesungLeee/gguk-wiki" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "gguk-wiki@gguk": true }
}
```

**버전과 업데이트**

- `version`을 적지 않는다. 버전은 레포의 커밋 SHA가 되고, 자동 업데이트(`autoUpdate: true`)로 새 커밋을 받는다. 서드파티 마켓플레이스는 자동 업데이트가 기본으로 꺼져 있어 켜 둔다([Claude Code 설정 문서](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)).
- 같은 마켓플레이스가 여러 설정 파일에 있으면 우선순위가 높은 파일의 항목을 쓴다. 사용자 범위 설치는 `autoUpdate` 없이 사용자 설정에 마켓플레이스를 등록하므로, 자동 업데이트는 위 4개 레포에서 연 세션에서 돈다.
- 플러그인 밖의 커밋(ingest merge, CI 재생성)도 버전을 바꾼다(2026-11-13 확인). 그래서 merge마다 업데이트 알림(`Plugin updated … Run /reload-plugins`)이 뜬다. 규칙은 호출마다 fetch해 주입하므로 업데이트를 미뤄도 규칙은 최신이다.
- `version`을 지정하는 안은 제외했다. 플러그인을 고칠 때만 업데이트되지만, 고칠 때마다 버전을 올려야 하고 잊으면 아무에게도 전달되지 않는다.

## 작업 공간

사용법: [README.md 작업 공간 준비](../README.md#작업-공간-준비), 동작: [`scripts/setup-workspace.sh`](../scripts/setup-workspace.sh)

ingest와 ask 스킬이 레포 위치를 묻지 않도록, 레포 4개를 정해진 폴더 하나(작업 공간, 기본 `~/gguk/`) 아래에 둔다.

- 위치는 `GGUK_HOME` 환경 변수, 설정 스크립트가 기록한 `~/.config/gguk/home`(`XDG_CONFIG_HOME`을 따른다), `~/gguk` 순으로 정한다.
- 다른 위치에 두려면 그 위치에 위키를 clone하고 설정 스크립트를 실행한다. 스크립트가 위치를 기록하므로 셸 설정이나 Claude Code 설정을 고치지 않아도 된다. 환경 변수만 쓰면 셸 설정 파일과 `~/.claude/settings.json`의 `env` 두 곳을 고쳐야 하고, 데스크톱 앱이나 IDE는 셸 설정을 읽지 않을 수 있다.
- 플러그인 설치 설정(`userConfig`)으로 폴더를 받는 안은 제외했다. 값을 저장하기 전에는 기본값이 주입 명령에 들어가지 않고 글자 그대로 남아 스킬 호출이 중단됐다(2026-11-13 확인).
- 작업용 clone이 따로 있어도 여기에 별도로 clone한다. 세 레포를 합쳐 약 64MB라 부담이 작고, 링크로 재사용하면 Windows에서 동작이 달라진다(Git Bash의 `ln -s`는 기본 설정에서 복사본을 만든다).
- ingest와 ask는 같은 위키 clone을 쓴다. ingest는 이 clone에서 작업 브랜치를 만들지만, ask는 `origin/HEAD`를 읽으므로 영향을 받지 않는다([읽는 기준](retrieval.md#읽는-기준)).
- 레포가 없으면 두 스킬 모두 설정 스크립트 실행을 안내한다.

**설정 스크립트 `scripts/setup-workspace.sh`**

- `GGUK_HOME`이 없으면 스크립트가 든 위키 clone의 상위 폴더를 작업 공간으로 쓴다. `GGUK_HOME`이 그 위치와 다르면 안내하고 `GGUK_HOME`을 쓴다.
- 작업 공간 위치를 기록하지 못하면 실패로 요약하고 `GGUK_HOME` 설정을 안내한다.
- `gh`가 없거나 로그인되어 있지 않아도 멈추지 않고 안내만 한다. 조회는 `gh` 없이 쓸 수 있고, 코드 레포가 모두 public이라 clone에 로그인이 필요 없다.
- Windows에서는 `core.longpaths=true`로 clone한다. 경로가 길면 checkout이 실패하기 때문이다.
- 한 레포가 실패해도 나머지를 계속 진행하고, 마지막에 레포별 상태를 요약한다. 일부만 실패했을 때 무엇을 다시 할지 알 수 있게 하기 위해서다.
- 여러 번 실행해도 결과가 같다. 레포가 추가되면 다시 실행한다.
- 개발자 PC에 Python 설치를 요구하지 않도록 bash로 쓴다. macOS 기본 bash(3.2)에서도 동작하게 쓴다.

## 필요 조건

| 항목 | 내용 |
| --- | --- |
| Claude Code | Pro 이상 구독. Free 플랜은 Claude Code를 쓸 수 없다 |
| git | Windows는 Git for Windows 또는 WSL이 필요하다. Git for Windows가 있으면 Claude Code의 Bash 도구가 Git Bash로 실행되어, macOS와 같은 명령이 동작한다 |
| gh | 로그인이 필요하다(`gh auth login`). ingest 스킬이 PR을 만들 때 쓴다. 조회만 하면 필요 없다 |
| 위키 레포 write 권한 | 협업자로 초대받아야 한다. 조회만 하면 필요 없다 |
| 노션 MCP (선택) | 노션 회의록을 MCP로 넣는 사람만 필요하다. `claude mcp add --transport http notion https://mcp.notion.com/mcp`로 추가한 뒤 `/mcp`에서 OAuth로 인증한다. 노션 워크스페이스 멤버여야 하고, 게스트는 연결할 수 없다 |

노션 MCP의 서버 이름은 `notion`으로 맞춘다. ingest 스킬은 `notion-search`, `notion-fetch`만 허용 도구(`mcp__notion__notion-search`, `mcp__notion__notion-fetch`)로 적는다. 서버 이름이 다르면 이 이름이 맞지 않아 매번 허락을 묻는다. 다른 노션 도구는 Claude Code가 실행 전에 허락을 묻는다.

노션 회의록을 내보내기로 넣을 때, Windows에서는 경로가 길면 압축 해제가 실패하므로 짧은 경로에 푼다.

## 다른 LLM 도구 지원 (1단계 확장)

Claude Code가 아닌 LLM 도구를 쓰는 팀원도 같은 위키를 쓰게 한다. 처음부터 다른 도구도 읽을 수 있는 형식으로 써 두고, 배포는 확장 단계에서 정한다.

- 위키 운영 규칙의 진입점은 `AGENTS.md`다. Codex, Gemini CLI, Cursor, GitHub Copilot 등이 읽는 파일이다. `AGENTS.md`가 상황별로 읽을 `procedures/` 파일을 안내한다.
- `CLAUDE.md`에는 `@AGENTS.md` 한 줄만 둔다. Claude Code는 `CLAUDE.md`가 있으면 `AGENTS.md`를 따로 읽지 않으므로 import로 연결한다.
- 스킬은 공개 형식인 SKILL.md로 쓴다. Codex와 Gemini CLI도 이 형식을 읽지만, 도구마다 읽는 폴더가 다르다(Codex는 `.agents/skills/`, Claude Code는 플러그인이나 `.claude/skills/`).
- SKILL.md의 `` !`명령` `` 주입은 Claude Code 전용이다. 다른 도구용 스킬에는 주입 대신 지시문을 적는다. 예: ask는 "먼저 작업 공간을 정한다(`GGUK_HOME`, `~/.config/gguk/home`, `~/gguk` 순, [작업 공간](#작업-공간)). 그다음 `git -C <작업 공간>/gguk-wiki show origin/HEAD:AGENTS.md`와 `origin/HEAD:procedures/ask.md`를 실행해 읽고 따른다". ingest는 [주입하는 파일](#구성)을 모두 읽게 한다.
- 설정 스크립트는 bash다. PowerShell만 쓰는 도구가 있으면 PowerShell 판을 검토한다.

**지원 기준**: `AGENTS.md`와 `procedures/`를 읽고 셸 명령(`git`, `gh`)을 실행할 수 있는 에이전트형 도구면 지원 대상으로 본다. 팀원별 도구는 조사하지 않는다.

- 동작 검증은 Claude Code만 한다. 다른 도구는 쓰는 팀원이 나오면 그 도구로 확인하고, 그 도구가 읽는 폴더에 스킬을 추가한다.
- 웹 채팅 전용 도구(ChatGPT, Gemini, Claude 웹앱 등)는 로컬 clone을 읽거나 `gh`를 실행할 수 없어 지원하지 않는다. 지원하려면 [MCP 서버](backlog/mcp-server.md)가 필요하다.
- 에이전트형 도구를 쓸 수 없는 팀원은 설치 안내 때 직접 알린다. 무료 플랜으로는 쓸 수 없는 도구가 있다. 예: Claude Free 플랜은 Claude Code를 쓸 수 없다([필요 조건](#필요-조건)).
