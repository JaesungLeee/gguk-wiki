---
name: ingest
description: GGUK 위키에 회의록, 기획 문서(PRD, 스펙), 노션 페이지, STT 요약, 채팅으로 받은 결정을 넣을 때 쓴다. 원본을 raw/에 남기고 결정·액션 아이템·미결 사항으로 나눠 PR을 만든다.
argument-hint: <파일 경로 | 노션 URL | 넣을 내용>
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh *)
  - mcp__notion__notion-search
  - mcp__notion__notion-fetch
---
아래는 GGUK 위키 default 브랜치의 공통 규칙(`AGENTS.md`), ingest 규칙(`procedures/ingest.md`), 도메인 목록(`domains.yml`), 문서 형식(`templates/`)이다. 이 규칙을 따라 위키에 넣는다.

- 맨 위가 `[GGUK 위키 규칙을 읽지 못함]`이면 규칙 없이 진행하지 않는다. 다른 작업을 하지 말고 그 안내를 사용자에게 그대로 전한 뒤 멈춘다.
- 입력이 비어 있으면 대화에서 사용자가 넣어 달라고 한 내용을 입력으로 삼는다. 그것도 없으면 무엇을 넣을지 묻는다.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh" AGENTS.md procedures/ingest.md domains.yml templates/decision.md templates/action-items.md templates/open-questions.md templates/note.md`

입력: $ARGUMENTS
