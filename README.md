# gguk-wiki

GGUK 프로젝트의 정책, 결정, 회의록, 기획 문서를 LLM이 관리하는 위키다. 팀원은 각자 PC의 Claude Code로 위키에 정보를 넣고(ingest), 위키와 코드 레포를 함께 조회한다(ask).

처음 쓸 때 [작업 공간을 준비](#작업-공간-준비)하고 [플러그인을 설치](#플러그인-설치)한다. 필요한 도구와 권한은 [필요 조건](docs/plugin.md#필요-조건)에 있다.

## 작업 공간 준비

위키와 코드 레포 3개를 한 폴더 아래에 둔다. 스킬이 레포 위치를 묻지 않고 이 폴더를 읽는다.

```text
~/gguk/                  # GGUK_HOME. 바꾸려면 환경 변수 GGUK_HOME을 설정한다
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

- 코드 레포 3개를 clone한다. 이미 있는 레포는 건너뛰므로 여러 번 실행해도 된다.
- 끝나면 레포별 상태를 보여 준다. 실패한 레포가 있으면 이유를 확인하고 다시 실행한다.
- 작업용 clone이 따로 있어도 이 폴더에 별도로 clone한다.
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

- 명령 없이 GGUK의 정책이나 다른 플랫폼 구현을 물어도 Claude가 필요하면 ask를 부른다.
- ingest가 받는 입력(회의록 파일, 노션 URL, STT 요약, 채팅 등)은 [ingest 규칙](procedures/ingest.md#입력)에 있다.
- 두 스킬은 호출할 때마다 위키 default 브랜치에서 규칙을 읽는다. 규칙이 바뀌어도 플러그인을 업데이트할 필요가 없다.
- 노션 회의록을 MCP로 넣으려면 노션 MCP를 `notion`이라는 이름으로 추가하고 `/mcp`에서 인증한다. 노션 워크스페이스 멤버만 연결할 수 있다.
  ```bash
  claude mcp add --transport http notion https://mcp.notion.com/mcp
  ```

## 플러그인 업데이트

위키 레포와 코드 레포에서 연 세션은 플러그인을 자동으로 업데이트한다. `Plugin updated` 알림이 뜨면 `/reload-plugins`를 실행하거나 새 세션을 연다. 직접 업데이트하려면 다음을 실행한다.

```bash
claude plugin marketplace update gguk
claude plugin update gguk-wiki@gguk
```

## 레포 구성

| 위치 | 내용 |
| --- | --- |
| [`raw/`](raw/) | 원본 자료(회의록, 기획 문서, 채팅). 넣은 뒤 고치지 않는다 |
| [`wiki/`](wiki/) | 결정, 액션 아이템, 미결 사항, 용어집. 도메인 페이지와 목차는 CI가 만든다 |
| [`AGENTS.md`](AGENTS.md) | LLM이 따르는 공통 규칙 |
| [`procedures/`](procedures/) | 스킬별 규칙: [ingest](procedures/ingest.md), [ask](procedures/ask.md) |
| [`templates/`](templates/) | 문서 형식. [회의록 템플릿](templates/meeting.md)은 노션 템플릿으로 복사해 쓴다 |
| [`domains.yml`](domains.yml) | 도메인 목록 |
| [`scripts/`](scripts/) | 생성 파일 만들기, 형식 검사, 작업 공간 설정 스크립트 |
| [`plugin/`](plugin/) | Claude Code 플러그인(ingest, ask 스킬). 마켓플레이스 정의는 [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) |
| [`docs/`](docs/README.md) | 설계 문서: 규칙을 정한 이유, 검토한 대안, 로드맵 |
