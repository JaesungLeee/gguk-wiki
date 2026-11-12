# GGUK 위키 운영 규칙

GGUK 위키에 정보를 넣고(ingest) 조회할 때 따르는 규칙이다.

- 위키에 넣을 때는 [`procedures/ingest.md`](procedures/ingest.md), 조회할 때는 [`procedures/ask.md`](procedures/ask.md)를 먼저 읽고 따른다. Claude Code의 ingest·ask 스킬은 이 파일들을 자동으로 주입한다.
- 문서 형식과 상태 값의 의미는 [`templates/`](templates/), 도메인 목록은 [`domains.yml`](domains.yml), 규칙을 정한 이유는 [`docs/`](docs/README.md)에 있다. 설치와 사용 안내는 [`README.md`](README.md)에 있다.
- 위키 본문은 한국어로 쓴다. 코드 용어(심볼명, 경로)는 영어 원문을 유지한다.
- 레포는 `${GGUK_HOME:-~/gguk}` 아래에 있다. 규칙 문서의 `~/gguk`는 이 경로를 뜻한다.

## 위키 구조

```text
raw/                    # 원본. 넣은 뒤 고치거나 지우지 않는다
├── meetings/           # 회의록 (파일, 노션 페이지, STT 요약)
├── specs/              # PRD, 스펙 문서
└── notes/              # 채팅으로 받은 내용
wiki/
├── decisions/          # 결정 1건 = 파일 1개
├── action-items/       # 원본 1건의 액션 아이템 = 파일 1개
├── open-questions/     # 원본 1건의 미결 사항 = 파일 1개
├── glossary.md         # 용어집
├── domains/            # 자동 생성. 도메인별 결정·미결 목록
├── index.md            # 자동 생성. 도메인 목차
├── log.md              # 자동 생성. 결정 시간순 목록
└── action-items.md     # 자동 생성. 열린 액션 아이템 기한순 목록
procedures/             # 스킬별 규칙 (ingest, ask)
templates/              # 문서 형식
domains.yml             # 도메인 목록
```

- `raw/`의 파일은 넣은 뒤 고치거나 지우지 않는다.
- 자동 생성 파일(`wiki/domains/`, `index.md`, `log.md`, `action-items.md`)은 만들거나 고치지 않는다. merge 뒤 CI가 다시 만든다.

## 진실의 기준

| 영역 | 기준 |
| --- | --- |
| 정책·의도 | 가장 최근의 유효한 결정(`decided`) |
| 화면 디자인 | Figma. 위키에는 디자인 결정만 남기고 화면 정의(치수, 색 값 등)는 옮기지 않는다 |
| 실제 동작 | 코드 (각 레포의 default 브랜치) |

서로 다르면 자동으로 고치지 않는다. 위키와 코드가 다르면 조회 답변에 불일치로 표시한다([답변 형식](procedures/ask.md#답변-형식)). 기획 문서와 디자인 결정이 다르면 ingest할 때 표시한다([중복·충돌 확인](procedures/ingest.md#중복충돌-확인)).

