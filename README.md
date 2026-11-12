# gguk-wiki

GGUK 프로젝트의 정책, 결정, 회의록, 기획 문서를 LLM이 관리하는 위키다. 팀원은 각자 PC의 Claude Code로 위키에 정보를 넣고(ingest), 위키와 코드 레포를 함께 조회한다(ask).

지금은 1단계 준비 중이다. Claude Code 플러그인이 완성되면 설치와 사용법을 이 문서에 추가한다([로드맵](docs/README.md#로드맵)).

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
| [`docs/`](docs/README.md) | 설계 문서: 규칙을 정한 이유, 검토한 대안, 로드맵 |
