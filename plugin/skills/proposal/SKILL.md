---
name: proposal
description: 위키의 기획 결정으로 GGUK 공용 기획서(proposal/project-proposal.md)를 만들거나 갱신할 때 쓴다. 지난 기획서 뒤로 바뀐 결정·미결을 찾아 항목별 개정 등급을 제안하고, 확인받아 PR을 만든다.
argument-hint: [갱신 이유나 범위]
model: opus
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh *)
---
아래는 GGUK 위키 default 브랜치의 공통 규칙(`AGENTS.md`), 기획서 규칙(`procedures/proposal.md`), 도메인 목록(`domains.yml`), 기획서 형식(`templates/`)이다. 이 규칙을 따라 기획서를 만들거나 갱신한다.

- 맨 위가 `[GGUK 위키 규칙을 읽지 못함]`이면 규칙 없이 진행하지 않는다. 다른 작업을 하지 말고 그 안내를 사용자에게 그대로 전한 뒤 멈춘다.
- 입력이 비어 있으면 위키 전체에서 반영할 변화를 찾는다.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh" AGENTS.md procedures/proposal.md domains.yml templates/proposal.md templates/proposal-sources.yml`

입력: $ARGUMENTS
