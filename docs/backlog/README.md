# Backlog

[1단계 범위](../README.md#1단계-범위)에 넣지 않은 설계를 모아 둔다. 꺼내 쓸 때는 본문 문서로 규칙을 옮기고 여기서는 지운다.

| 문서 | 내용 | 미룬 이유 | 다시 검토할 신호 |
| --- | --- | --- | --- |
| [mcp-server.md](mcp-server.md) | MCP 서버, 도구 목록, 서버 지시문 | 1단계는 각자의 Claude Code가 로컬 clone을 직접 읽는다 | Claude Code 밖(디스코드, Claude Desktop)에서 위키를 써야 할 때 |
| [discord-bot.md](discord-bot.md) | 디스코드 봇, `#회의록` 업로드, [반영] 버튼 | 서버와 API 키가 필요하다 | Claude Code를 쓰지 않는 사람의 입력·조회 수요가 생길 때 |
| [hosting/](hosting/README.md) | AWS 호스팅 서버 | MCP 서버나 봇이 있어야 필요하다 | 위 둘 중 하나를 도입할 때 |
| [hooks.md](hooks.md) | 세션 시작 훅, 프롬프트 입력 훅 | 묻지 않아도 알려 주는 확장 기능이고, 매 세션 토큰 비용을 개인 구독이 부담한다 | 정책이 바뀐 걸 몰라 다시 작업한 사례가 생길 때 |
| [search-upgrades.md](search-upgrades.md) | 형태소 분석기 정규화, 검색 평가셋, 벡터 DB, `report_gap` | 1단계는 LLM이 검색어를 만든다 | 위키에 답이 있는데 못 찾는 사례가 반복될 때 |
| [automation.md](automation.md) | 주간 lint, 변경 알림, PR 리뷰 봇, 검색 기록과 성과 측정 | API 키, 서버, 알림 채널이 필요하다 | 위키가 쌓여 오래된 페이지가 생길 때 |
| [ideas.md](ideas.md) | 확장 추천 사례 | 후보 목록 | |
