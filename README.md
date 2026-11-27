# gguk-wiki

GGUK 프로젝트의 정책, 결정(플랫폼 공통 계약·기술 결정 포함), 회의록을 LLM이 관리하는 위키다. 팀원은 각자 PC의 Claude Code, Codex, Pi로 위키에 정보를 넣고(ingest), 위키와 코드 레포를 함께 조회하고(ask), 위키 결정으로 공용 기획서를 갱신한다(proposal).

처음 쓸 때 [작업 공간을 준비](#작업-공간-준비)한다. Claude Code는 [플러그인을 설치](#플러그인-설치)하고, Codex와 Pi는 [작업 공간 준비만으로 스킬이 설치된다](#codex와-pi). 필요한 도구와 권한은 [필요 조건](docs/plugin.md#필요-조건)에 있다.

## 작업 공간 준비

위키와 코드 레포 3개를 한 폴더 아래에 둔다. 스킬이 레포 위치를 묻지 않고 이 폴더를 읽는다.

```text
~/gguk/                  # 작업 공간. 다른 폴더에 둘 수 있다
├── gguk-wiki/
├── Team-MINO-Node/
├── Team-MINO-Android/
└── Team-MINO-iOS/
```

처음에 한 번 실행한다. Windows에서는 Git Bash에서 실행한다.

```bash
git clone https://github.com/JaesungLeee/gguk-wiki.git ~/gguk/gguk-wiki
~/gguk/gguk-wiki/scripts/setup-workspace.sh
```

- 다른 폴더에 두려면 두 명령의 `~/gguk`을 그 폴더로 바꿔 실행한다. 설정 스크립트가 위치를 기록하므로 따로 설정할 것은 없다.
- 코드 레포 3개를 clone한다. 이미 있는 레포는 건너뛰므로 여러 번 실행해도 된다.
- 끝나면 레포별 상태와 작업 공간 위치 기록 결과를 보여 준다. 실패한 항목이 있으면 이유를 확인하고 다시 실행한다.
- 작업용 clone이 따로 있어도 이 폴더에 별도로 clone한다.
- Codex·Pi용 스킬을 `~/.agents/skills/`에 링크한다. 이 폴더에 같은 이름의 다른 스킬이 있으면 건드리지 않고 실패로 알린다.
- 위키에 정보를 넣으려면(ingest) `gh`를 설치하고 `gh auth login`으로 로그인한다. 조회만 하면 필요 없다.

## 플러그인 설치

처음에 한 번 실행한다. Claude Code v2.1.292 이상이 필요하다.

```bash
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
claude plugin install gguk-wiki --marketplace JaesungLeee/gguk-wiki --scope user
```

- `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`은 GitHub SSH 키가 없는 사람에게 필요하다. 없으면 플러그인 업데이트가 실패하므로 셸 설정 파일(`~/.zshrc`, `~/.bashrc`)에도 넣는다. Windows에서 PowerShell로 Claude Code를 실행하면 `setx CLAUDE_CODE_PLUGIN_PREFER_HTTPS 1`로 설정한다.
- `--scope user`로 설치하면 코드 레포 3곳과 위키 레포 어디서든 쓸 수 있다.
- 열려 있는 세션에는 `/reload-plugins`를 실행해야 적용된다.

## 사용법

| 명령 | 예 |
| --- | --- |
| `/gguk-wiki:ask <질문>` | `/gguk-wiki:ask 보관함에서 방을 지우면 어떻게 돼?` |
| `/gguk-wiki:ingest <입력>` | `/gguk-wiki:ingest ~/Downloads/2026-11-10-결제-정책.md` |
| `/gguk-wiki:proposal [범위]` | `/gguk-wiki:proposal` (위키에서 바뀐 결정을 찾아 기획서 갱신 PR을 만든다) |

- 명령 없이 GGUK의 정책이나 다른 플랫폼 구현을 물어도 Claude가 필요하면 ask를 부른다.
- ingest가 받는 입력(회의록 파일, 노션 URL, STT 요약, 채팅 등)은 [ingest 규칙](procedures/ingest.md#입력)에 있다.
- 기획서는 [`proposal/project-proposal.md`](proposal/)다. 직접 고치지 않는다. 바꿀 내용은 ingest로 위키에 넣고 merge한 뒤 proposal로 갱신한다([기획서 규칙](procedures/proposal.md)).
- 스킬은 호출할 때마다 위키 default 브랜치에서 규칙을 읽는다. 규칙이 바뀌어도 플러그인을 업데이트할 필요가 없다.
- 노션 회의록을 MCP로 넣으려면 노션 MCP를 `notion`이라는 이름으로 추가하고 `/mcp`에서 인증한다. 노션 워크스페이스 멤버만 연결할 수 있다.
  ```bash
  claude mcp add --transport http notion https://mcp.notion.com/mcp
  ```

## Codex와 Pi

[작업 공간 준비](#작업-공간-준비)의 설정 스크립트가 스킬 `gguk-ask`, `gguk-ingest`, `gguk-proposal`을 `~/.agents/skills/`에 링크한다. Codex와 Pi 모두 이 폴더를 읽으므로 따로 설치할 것은 없다. 열려 있는 세션에서 스킬이 보이지 않으면 새 세션을 연다.

| 도구 | 조회 | 넣기 | 기획서 갱신 |
| --- | --- | --- | --- |
| Codex | `$gguk-ask 보관함에서 방을 지우면 어떻게 돼?` | `$gguk-ingest ~/Downloads/2026-11-10-결제-정책.md` | `$gguk-proposal` |
| Pi | `/skill:gguk-ask 보관함에서 방을 지우면 어떻게 돼?` | `/skill:gguk-ingest ~/Downloads/2026-11-10-결제-정책.md` | `/skill:gguk-proposal` |

- 명령 없이 물어도 도구가 필요하면 스킬을 부른다. 부르지 않으면 위 명령으로 직접 부른다.
- 스킬은 호출할 때마다 위키 default 브랜치에서 규칙을 읽는다. 규칙이 바뀌어도 다시 설치할 필요가 없다. Windows에서는 링크 대신 복사본이 설치되므로, `agents/skills/`가 바뀌면 설정 스크립트를 다시 실행한다.
- Codex의 샌드박스가 네트워크나 위키 clone 쓰기를 막으면 규칙과 코드를 fetch하지 못하고 마지막으로 받은 상태를 읽는다. 이때 답에 기준 시각이 붙는다. ingest와 proposal의 브랜치 생성, 커밋, PR은 승인을 받아 실행한다.
- Pi는 명령을 실행하기 전에 허락을 묻지 않는다. ingest와 proposal은 PR을 만들기 전에 변경 요약과 확인 항목을 보여 주고 확인을 받는다.
- 노션 회의록을 MCP로 넣으려면 각 도구의 MCP 설정에 노션 MCP(`https://mcp.notion.com/mcp`)를 `notion`이라는 이름으로 추가한다. Codex는 `codex mcp add notion --url https://mcp.notion.com/mcp`로 추가하고, Pi는 `~/.pi/agent/mcp.json`에 적는다. 노션 워크스페이스 멤버만 연결할 수 있다.

## 플러그인 업데이트

위키 레포와 코드 레포에서 연 세션은 플러그인을 자동으로 업데이트한다. `Plugin updated` 알림이 뜨면 `/reload-plugins`를 실행하거나 새 세션을 연다. 직접 업데이트하려면 다음을 실행한다.

```bash
claude plugin marketplace update gguk
claude plugin update gguk-wiki@gguk
```

## 레포 구성

| 위치 | 내용 |
| --- | --- |
| [`raw/`](raw/) | 원본 자료(회의록, 이관 기준선 기획서, 채팅). 넣은 뒤 고치지 않는다 |
| [`wiki/`](wiki/) | 결정, 액션 아이템, 미결 사항, 용어집. 도메인 페이지와 목차는 CI가 만든다 |
| [`proposal/`](proposal/) | 위키에서 뽑은 공용 기획서와 근거 대응표. proposal 스킬로만 고친다 |
| [`AGENTS.md`](AGENTS.md) | LLM이 따르는 공통 규칙 |
| [`procedures/`](procedures/) | 스킬별 규칙: [ingest](procedures/ingest.md), [ask](procedures/ask.md), [proposal](procedures/proposal.md) |
| [`templates/`](templates/) | 문서 형식. [회의록 템플릿](templates/meeting.md)은 노션 템플릿으로 복사해 쓴다 |
| [`domains.yml`](domains.yml) | 도메인 목록 |
| [`people.yml`](people.yml) | 팀원 목록. 채팅 원본의 말한 사람(`author`)과 액션 아이템 담당자(`assignee`)를 이 이름으로 적는다. 목록에 없는 사람은 "알 수 없음" |
| [`platform-repository.yml`](platform-repository.yml) | 플랫폼별 코드 레포 목록. 설정 스크립트가 이 목록으로 clone하고, 스킬이 이 목록으로 레포를 찾는다 |
| [`scripts/`](scripts/) | 생성 파일 만들기, 형식 검사, 작업 공간 설정 스크립트 |
| [`plugin/`](plugin/) | Claude Code 플러그인(ingest, ask, proposal 스킬). 마켓플레이스 정의는 [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) |
| [`agents/skills/`](agents/skills/) | Codex·Pi용 스킬(`gguk-ingest`, `gguk-ask`, `gguk-proposal`) |
| [`docs/`](docs/README.md) | 설계 문서: 규칙을 정한 이유, 검토한 대안, 로드맵 |
