# 호스팅 서버

디스코드 봇과 MCP 서버를 운영할 서버 구성을 정한다. [MCP 서버](../mcp-server.md)나 [디스코드 봇](../discord-bot.md)을 도입할 때 필요하고, 1단계는 서버 없이 운영한다([1단계 범위](../../README.md#1단계-범위)). 도구 목록은 [MCP 도구](../mcp-server.md#mcp-도구)를 따른다.

> 상태: backlog. 미룬 이유는 [backlog/](../README.md)를 따른다. 도입할 때는 AWS 별도 서버와 도메인 신규 구매를 기본으로 하고, 나머지는 구축하면서 확정한다.

## 문서 목록

| 문서 | 내용 |
| --- | --- |
| [infra.md](infra.md) | AWS 인프라: EC2, 네트워크, 인스턴스 역할 |
| [app.md](app.md) | 구현 스택, 앱 구조, 저장소 구조 |
| [security.md](security.md) | 외부 노출과 인증, 권한과 비밀값 |
| [deploy.md](deploy.md) | 레포 최신화, 배포, 모니터링과 백업 |

## 결정 사항

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 서버 위치 | AWS에 위키 전용 서버를 따로 둔다 | 제품 인프라와 장애·권한을 분리한다. 코드 clone과 API 키를 운영 환경 가까이에 두지 않는다 |
| 제외한 대안 | 사내 서버, 기존 백엔드 인프라 | 사내 서버는 외부 노출과 하드웨어 관리 부담이 크다. 기존 인프라는 제품과 엮인다 |
| 도메인 | 새로 구매한다 (Cloudflare Registrar) | Cloudflare Tunnel을 쓰려면 DNS가 Cloudflare에 있어야 한다 |
| 구현 언어 | Python | [구현 스택](app.md#구현-스택) 참고 |

## 실행 위치

서버에는 항상 떠 있어야 하는 것만 둔다. 이벤트로 실행되는 작업은 GitHub Actions에서 돌린다.

| 구성 요소 | 실행 위치 | 이유 |
| --- | --- | --- |
| 디스코드 봇 | 서버 | Gateway 연결을 유지해야 회의록 첨부와 👍/👎 반응을 받는다 |
| MCP 서버 | 서버 | 봇, Claude Code, Claude Desktop이 접속한다 |
| 위키 + 코드 레포 3개 clone | 서버 | `search_wiki`, `search_code`가 로컬 디스크에서 grep한다 |
| 검색 기록 (sqlite) | 서버 볼륨 | git 밖에 있는 유일한 상태 |
| Ingest 에이전트 | Actions | 수 분 걸리는 Opus 작업이 봇을 붙잡지 않는다. 실행 로그가 PR 옆에 남는다 |
| 인덱스 생성, 형식 검사, PR 리뷰 | Actions | [인덱스 생성과 형식 검사](../../ingest.md#인덱스-생성과-형식-검사) |
| 주간 lint, 48시간 리마인드 | Actions (schedule) | [자동화](../automation.md) |

- 서버리스(Lambda 등)는 쓰지 않는다. Gateway 상시 연결과 grep용 로컬 디스크가 모두 필요하다.
- 서버는 언제든 버리고 다시 만들 수 있게 둔다. 위키·결정·인덱스는 git에 있고, 서버에만 있는 것은 sqlite 검색 기록뿐이다.

**회의록 업로드에서 서버와 Actions의 경계**

1. 봇이 `#회의록` 첨부 파일을 GitHub App 토큰으로 `raw/meetings/`에 커밋한다. 이 App은 main 보호 규칙의 우회 대상이다([main 보호 규칙](../../ingest.md#main-보호-규칙)).
2. `raw/meetings/**` push가 Ingest 워크플로를 실행해 PR을 만든다.
3. 워크플로가 디스코드 웹훅으로 결정사항 요약과 PR 링크를 보낸다.

업로드 절차는 [회의록 업로드 채널](../discord-bot.md#회의록-업로드-채널), 반영 규칙은 [ingest.md](../../ingest.md)를 따른다.

## 구성도

```text
[EC2, 서울 리전]
  cloudflared ──▶ app :8080 (FastAPI + MCP) ◀── bot (discord.py) ──▶ 디스코드
                   │
                   ├─ volume repos/  위키 + 코드 3개 clone (읽기 전용)
                   └─ volume data/   sqlite 검색 기록
  syncer ──▶ 5분마다 git fetch ──▶ repos/

[외부]
  Claude Code (개발자 PC) ──HTTPS──▶ Cloudflare ──터널──▶ cloudflared
  GitHub Actions: Ingest, CI, lint / 이미지 빌드 → ECR → SSM으로 배포
  운영자 셸: SSM Session Manager
  백업: S3
```

- 외부에서 서버로 들어오는 포트는 없다. cloudflared, 봇, syncer 모두 서버에서 밖으로 연결한다.
- 밖으로 노출하는 것은 app 하나다.

## 구축 순서

| # | 작업 | 완료 기준 |
| --- | --- | --- |
| 0 | 도메인 구매, Cloudflare Tunnel 생성 | 터널 토큰 발급 |
| 1 | EC2, 보안 그룹, 인스턴스 역할, `bootstrap.sh` (Docker, 자동 업데이트, 로그 제한) | SSM으로 셸 접속, 인바운드 포트 0개 |
| 2 | GitHub App, syncer | `repos/`에 레포 4개가 받아지고 5분마다 최신화됨 |
| 3 | app: `search_wiki`, `read_page`, `search_code` + 토큰 인증 | 내 PC의 Claude Code에서 터널 URL로 검색됨 |
| 4 | [검색 평가셋](../search-upgrades.md#검색-평가셋)을 서버 검색으로 실행 | R@5가 기준을 넘음 |
| 5 | 봇: `/ask`, 스레드, 👍/👎 기록 | 테스트 채널에서 출처가 붙은 답변이 나옴 |
| 6 | 회의록 첨부 → 커밋 → Actions Ingest → 웹훅 알림 | `#회의록` 업로드 후 PR이 만들어지고 디스코드에 알림 |
| 7 | 배포 자동화, 모니터링, 백업 | 서버를 지우고 다시 만들어 30분 안에 복구됨 |

3~4번 작업이 끝난 뒤 플러그인에 MCP 설정을 추가한다. 코드 레포 쪽 설정은 바꾸지 않는다([도입할 때 바뀌는 것](../mcp-server.md#도입할-때-바뀌는-것)).

## 비용 항목

| 항목 | 성격 |
| --- | --- |
| EC2 `t3.medium` + EBS 80GB | 매월 고정 |
| S3 백업, ECR | 적음 |
| 도메인 | 연 1회 |
| Cloudflare Tunnel | 무료 |
| Anthropic API | 사용량에 비례하며 전체 비용의 대부분. workspace 지출 한도로 관리한다 |

## 구현 전 확인할 가정

- Claude Desktop과 claude.ai 커넥터가 Anthropic 클라우드에서 접속하는지, OAuth가 필요한지
- [구현 주의](app.md#앱-구조)의 FastMCP 동작이 쓰는 SDK 버전에서도 같은지
- claude-agent-sdk(Python)가 요구하는 Claude Code CLI가 컨테이너 이미지에 포함되는지
