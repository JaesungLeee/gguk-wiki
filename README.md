# gguk-wiki

GGUK 프로젝트의 정책, 결정, 회의록, 기획 문서를 LLM이 관리하는 위키다. 팀원은 각자 PC의 Claude Code로 위키에 정보를 넣고(ingest), 위키와 코드 레포를 함께 조회한다(ask).

지금은 1단계 준비 중이다. 설정 스크립트와 Claude Code 플러그인이 완성되면 설치와 사용법을 이 문서에 추가한다([로드맵](docs/README.md#로드맵)).

## 레포 구성

| 위치 | 내용 |
| --- | --- |
| [`raw/`](raw/) | 원본 자료(회의록, 기획 문서, 채팅). 넣은 뒤 고치지 않는다 |
| [`wiki/`](wiki/) | 결정, 액션 아이템, 미결 사항, 용어집. 도메인 페이지와 목차는 CI가 만든다 |
| [`AGENTS.md`](AGENTS.md) | LLM이 따르는 공통 규칙 |
| [`procedures/`](procedures/) | 스킬별 규칙: [ingest](procedures/ingest.md), [ask](procedures/ask.md) |
| [`templates/`](templates/) | 문서 형식. [회의록 템플릿](templates/meeting.md)은 노션 템플릿으로 복사해 쓴다 |
| [`domains.yml`](domains.yml) | 도메인 목록 |
| [`docs/`](docs/README.md) | 설계 문서: 규칙을 정한 이유, 검토한 대안, 로드맵 |
