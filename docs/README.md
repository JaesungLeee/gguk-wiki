# GGUK LLM Wiki 설계

- 작성일: 2026-11-10
- 수정일: 2026-11-11 (1단계 범위 재정의, 기존 자료 이관·입력 경로·액션 아이템 형식 추가, 문서 간 정합성 검토 반영, 미결 사항 결정: 기획 문서 반영 기준, 디자인 범위, 지원 도구 기준, 운영 방침 확정, 레포 준비 진행 상황), 2026-11-12 (위키 뼈대 작성: 규칙을 `AGENTS.md`·`procedures/`·`templates/`·`domains.yml`로 옮기고 설계 문서에는 이유만 남김, 도메인 13개 확정, 도메인 페이지 생성 방식·미결 형식·ADR 승격 기준 추가, 스크립트·CI·GitHub App 준비, ruleset을 1.3에서 한 번에 걸도록 순서 변경), 2026-11-13 (플러그인 추가, 작업 공간 위치 기록, 도메인 추가 절차 확정), 2026-11-14 (도메인 목록 팀 공유)
- 작성자: Jaesung Lee

## 개요

GGUK 프로젝트의 도메인 지식, 의사결정, 회의록, 기획서를 LLM이 관리하는 위키로 만들어 최신 상태로 유지하고, 참여 인력이 필요할 때 찾아 쓰게 한다.

| 항목 | 내용 |
| --- | --- |
| 프로젝트 | GGUK (단일 프로젝트) |
| 참여 인력 | 12명: 디자이너 2, 백엔드 4, Android 3, iOS 3 |
| 코드 저장소 | 직무별 3개, 모두 public: [Team-MINO-Node](https://github.com/mash-up-kr/Team-MINO-Node) (서버), [Team-MINO-Android](https://github.com/mash-up-kr/Team-MINO-Android), [Team-MINO-iOS](https://github.com/mash-up-kr/Team-MINO-iOS) |
| 위키 저장소 | `JaesungLeee/gguk-wiki` (별도 git 저장소, public. [공개 범위](data-model.md#공개-범위)) |
| 협업 채널 | 디스코드 (1단계에서는 연동하지 않는다) |
| 회의록 형식 | 노션, STT 웹 요약(Alt), 마크다운(.md) ([입력](ingest.md#입력)) |
| 기획 문서 | PRD, 스펙 문서. 마크다운(.md). 기획자가 따로 없고, 팀 아이디에이션 → 디자인 → PRD 순으로 만든다 |
| 디자인 | Figma. 디자인 결정만 위키에 남기고 화면 정의는 Figma에 둔다([진실의 기준](data-model.md#진실의-기준-source-of-truth)) |
| LLM 사용 | 각자 PC의 Claude Code, 개인 구독 |

## 1단계 범위

1단계는 순수 knowledge 위키로만 쓴다. 서버, 봇, 자체 MCP 서버, API 키 없이 각자 PC의 Claude Code와 개인 구독으로 운영한다. 외부 서비스가 제공하는 MCP(노션 등)는 쓸 수 있다.

| # | 사례 | 핵심 규칙 |
| --- | --- | --- |
| 1 | 위키에 정보 넣기 | 회의록(노션, STT 요약, 파일), 기획 문서, 채팅으로 말한 내용을 Claude Code가 PR로 제안하고, 업로더가 확인해 merge한다. 원본은 `raw/`에 남기고, 결정은 덮어쓰지 않고 이력을 남긴다([ingest.md](ingest.md)) |
| 2 | 위키 조회 | 답변마다 출처를 붙이고, 대체된 결정은 빼고 답한다([retrieval.md](retrieval.md#위키-조회)) |
| 3 | 다른 레포 조회 | 작업 중인 레포에서 다른 플랫폼의 코드를 각 레포의 default 브랜치 기준으로 조회한다. 위키(정책)와 코드(실제 구현)가 다르면 [진실의 기준](data-model.md#진실의-기준-source-of-truth)을 따른다([코드 조회](retrieval.md#코드-조회)) |

**1단계 확장**: Claude Code가 아닌 LLM 도구를 쓰는 팀원도 같은 위키를 쓰게 한다([다른 LLM 도구 지원](plugin.md#다른-llm-도구-지원-1단계-확장)).

**1단계에서 하지 않는 것**: 디스코드 봇, 자체 MCP 서버, 호스팅 서버, Claude Code 훅, 자동 lint·알림, 검색 기록·성과 측정, 검색 고도화. 설계는 [backlog/](backlog/README.md)에 둔다.

## 문서 목록

규칙의 정본은 레포의 실행 파일이다. 이 폴더의 설계 문서는 규칙을 왜 그렇게 정했는지와 검토한 대안을 담는다.

| 정본 | 내용 |
| --- | --- |
| [`AGENTS.md`](../AGENTS.md) | 공통 규칙: 위키 구조, 진실의 기준 |
| [`procedures/`](../procedures/) | 스킬별 규칙: [ingest](../procedures/ingest.md), [ask](../procedures/ask.md) |
| [`templates/`](../templates/) | 문서 형식과 상태 값 |
| [`domains.yml`](../domains.yml) | 도메인 목록 |

| 문서 | 내용 | 상태 |
| --- | --- | --- |
| [data-model.md](data-model.md) | 저장 형식: 진실의 기준, 위키 구조·도메인·용어집, 공개 범위, 결정 문서·액션 아이템·미결 사항 형식, 회의록 템플릿 | 결정됨 |
| [ingest.md](ingest.md) | 쓰기 경로: 입력 → ingest 스킬 → PR → merge, 승인 구조, 용어집 반영, 기존 자료 이관, CI 검사·인덱스 생성(3번 전까지 사양), main 보호 규칙 | 결정됨 |
| [retrieval.md](retrieval.md) | 읽기 경로: 읽는 기준, 위키 조회, 질의 정규화, 코드 조회, 답변 형식 | 결정됨 |
| [plugin.md](plugin.md) | 클라이언트: 플러그인 구성, 설치와 배포, 작업 공간과 설정 스크립트, 필요 조건, 다른 LLM 도구 지원 | 결정됨 |
| [operations.md](operations.md) | 운영 방침: 스킬별 모델, 비용, 공개 범위, 언어 | 결정됨 |
| [backlog/](backlog/README.md) | 1단계에 넣지 않은 설계 | 후보 |

규칙은 정본 한 곳에만 적고, 설계 문서와 다른 문서에서는 링크로 가리킨다.

## 구조도

```text
[각자 PC]
  Claude Code (개인 구독) + gguk-wiki 플러그인
    ├─ ingest 스킬 ──▶ 브랜치 · 커밋 · gh pr create ──▶ [GitHub] gguk-wiki
    │    └─ 노션 MCP (선택, 노션 회의록을 넣는 사람만)
    └─ ask 스킬    ──▶ ~/gguk/ 로컬 clone을 default 브랜치 기준으로 읽기
                         ├─ gguk-wiki/
                         ├─ Team-MINO-Node/
                         ├─ Team-MINO-Android/
                         └─ Team-MINO-iOS/

[GitHub] gguk-wiki (public)
  ├─ ruleset: PR 필수(승인 0명), 형식 검사 통과 필수
  └─ Actions: PR 형식 검사 / merge 후 wiki/domains/·index.md·log.md·action-items.md 재생성 (GitHub App)
```

## 로드맵

| 단계 | 범위 |
| --- | --- |
| 1단계 | Claude Code로 위키 넣기·조회, 다른 레포 조회 |
| 1단계 확장 | 다른 LLM 도구 사용자 지원 |
| 이후 | [backlog/](backlog/README.md)에서 골라 정한다. 기존 2단계 안은 MCP 서버 + 디스코드 봇이다 |

**다음 단계**

1. 위키 레포를 준비한다. 순서를 지킨다.
   1. `LICENSE`(Apache 2.0)를 지운다. 공개 레포라도 라이선스가 없으면 재사용 권리를 주지 않는다([공개 범위](data-model.md#공개-범위)). **완료** (2026-11-11)
   2. 레포를 public으로 바꾼다. **완료** (2026-11-13 확인)
   3. ruleset을 설정한다. PR 필수(승인 0명), 형식 검사(`check`) 통과 필수, force push·브랜치 삭제 금지를 걸고, GitHub App `gguk-wiki-bot`을 우회 대상에 넣는다([main 보호 규칙](ingest.md#main-보호-규칙)). **보류** (1.2 뒤에 한다)
   4. 팀원을 협업자(write)로 초대한다. **보류** (1.3 뒤에 한다)

   1.2~1.4는 나중에 진행한다(2026-11-11). 그동안 2번부터 진행한다. 1.2는 완료했고 1.3부터 남았다(2026-11-13).
   - 1.3은 1.2가 끝나야 할 수 있다. Free 플랜의 private 레포에서는 ruleset을 쓸 수 없다.
   - 1.4는 1.3 뒤에 한다. ruleset 없이 초대하면 팀원이 main에 바로 푸시할 수 있다.
   - 형식 검사 CI와 GitHub App은 3번에서 먼저 만들었으므로 1.3에서 ruleset을 한 번에 건다.
2. 디렉터리 구조, 회의록 템플릿, 결정 문서 형식, 액션 아이템 형식, 용어집 형식, `AGENTS.md` 스키마(도메인 목록, ingest·조회 절차)를 작성한다. 작성 후에는 실제 파일을 기준으로 삼고, 설계 문서에는 이유만 남긴다. **완료** (2026-11-12)
   - 뼈대 파일(`AGENTS.md`, `procedures/`, `templates/`, `domains.yml`, `wiki/glossary.md`)은 [#3](https://github.com/JaesungLeee/gguk-wiki/pull/3), 설계 문서 정리는 그 뒤 PR에서 했다.
   - 작성하면서 미결 사항 형식(`wiki/open-questions/`), 생성 도메인 페이지, ADR 승격 기준을 더했다.
3. 인덱스 생성과 형식 검사 스크립트를 만들어 CI에 붙이고, `setup-workspace.sh`를 만든다. 생성 파일을 커밋할 GitHub App을 만든다. ruleset 설정은 1.3에서 한다. **완료** (2026-11-12)
   - 생성 대상: `wiki/domains/`, 2단 `index.md`, 결정 시간순 `log.md`, `action-items.md`([인덱스 생성과 형식 검사](ingest.md#인덱스-생성과-형식-검사))
   - 검사 대상에 미결 파일과 `domains.yml`을 넣고, 템플릿 샘플 테스트와 한글 파일 이름(NFD/NFC) 테스트를 둔다.
   - 설치·작업 공간 안내를 루트 `README.md`로 옮긴다.
   - 스크립트, 테스트, CI(PR 검사 `check`, merge 후 재생성), `setup-workspace.sh`는 [#5](https://github.com/JaesungLeee/gguk-wiki/pull/5)에서 만들었다. 작업 공간 안내는 그 뒤 PR에서 `README.md`로 옮겼다. **완료** (2026-11-12)
   - GitHub App `gguk-wiki-bot`을 만들어 `gguk-wiki`에만 설치하고 secrets(`WIKI_APP_ID`, `WIKI_APP_PRIVATE_KEY`)를 등록했다. 재생성 워크플로에서 App 토큰 발급을 확인했다. **완료** (2026-11-12)
4. 플러그인(ingest, ask 스킬)을 만들고 코드 레포 3곳과 위키 레포의 `.claude/settings.json`에 등록한다([설치와 배포](plugin.md#설치와-배포)).
   - 스킬별 주입 파일은 [구성](plugin.md#구성)을 따른다. ask는 `AGENTS.md`와 `procedures/ask.md`, ingest는 거기에 `procedures/ingest.md`, `domains.yml`, 템플릿 4개를 더한다.
   - 플러그인 사용법을 루트 `README.md`에 추가한다.
   - 플러그인과 위키 레포 등록은 [#8](https://github.com/JaesungLeee/gguk-wiki/pull/8), 작업 공간 위치 기록은 그 뒤 PR에서 했다. 코드 레포 3곳 등록이 남았다.
   - 코드 레포 등록보다 도메인 추가 절차([도메인](../procedures/ingest.md#도메인))를 먼저 정했다. **완료** (2026-11-13)
5. 회의록 몇 건으로 ingest를 검증하고, 실제 질문으로 위키 조회와 다른 레포 조회를 확인한다.
6. 기존 자료를 옮긴다. PRD·스펙으로 기준선을 만들고 노션 회의록으로 보충한다([기존 자료 이관](ingest.md#기존-자료-이관)).
7. 1단계 확장을 진행한다([지원 기준](plugin.md#다른-llm-도구-지원-1단계-확장)).

## 미결 사항

1단계 설계 미결 사항은 없다. 아래는 팀 확인이 필요한 항목이다(2026-11-12).

| # | 항목 | 언제까지 |
| --- | --- | --- |
| 1 | 도메인 목록 13개([`domains.yml`](../domains.yml))를 팀에 공유한다 | **완료** (2026-11-14) |
| 2 | 지도 클러스터 처리가 플랫폼마다 다르다. Android는 같은 방(색)의 핀끼리만 묶고, iOS는 여러 방을 섞어 회색으로 묶는다(Android `develop @ de058e2`, iOS `develop @ dca2202`). 디자인 결정이 필요하다 | — |
| 3 | Android ADR의 "무엇" 3건(글자 크기 고정, 지도 클러스터, Firebase 익명 인증)을 팀 결정으로 확인한다([ADR 승격](ingest.md#입력)) | 6번(이관) 전 |
| 4 | Node PRD(2.1장, 5장)에는 "`device_id` 기반 등록"으로 적혀 있지만, 세 플랫폼 코드는 모두 Firebase 익명 인증이다. 기준선으로 넣기 전에 PRD를 고칠지 정한다 | 6번(이관) 전 |

서버·봇 관련 미결 사항(호스팅 운영 담당자, 도메인 이름, 디자이너의 Claude Desktop 연동, 디스코드 대화 수집)은 [backlog/](backlog/README.md)의 각 문서로 옮겼다.
