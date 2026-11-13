---
name: ask
description: GGUK의 정책, 결정, 기획 의도, 미결 사항, 액션 아이템, 다른 플랫폼(Node, Android, iOS) 구현을 물을 때 쓴다. 위키와 코드 레포의 default 브랜치를 읽고 출처를 붙여 답한다.
argument-hint: <질문>
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh *)
  - Bash(git -C * fetch *)
  - Bash(git -C * remote set-head *)
  - Bash(git -C * grep *)
  - Bash(git -C * show *)
  - Bash(git -C * log *)
  - Bash(git -C * rev-parse *)
  - Bash(git -C * ls-tree *)
---
아래는 GGUK 위키 default 브랜치의 공통 규칙(`AGENTS.md`)과 조회 규칙(`procedures/ask.md`)이다. 이 규칙을 따라 질문에 답한다.

- 맨 위가 `[GGUK 위키 규칙을 읽지 못함]`이면 규칙 없이 진행하지 않는다. 다른 작업을 하지 말고 그 안내를 사용자에게 그대로 전한 뒤 멈춘다.
- 질문이 비어 있으면 대화에서 사용자가 물은 내용에 답한다.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/wiki-show.sh" AGENTS.md procedures/ask.md`

질문: $ARGUMENTS
