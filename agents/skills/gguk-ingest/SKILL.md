---
name: gguk-ingest
description: GGUK 위키에 회의록, 노션 페이지, STT 요약, 채팅으로 받은 결정을 넣을 때 쓴다. 원본을 raw/에 남기고 결정·액션 아이템·미결 사항으로 나눠 PR을 만든다.
---
가장 먼저 아래 명령을 실행해 GGUK 위키 default 브랜치의 공통 규칙(`AGENTS.md`), ingest 규칙(`procedures/ingest.md`), 도메인 목록(`domains.yml`), 팀원 목록(`people.yml`), 문서 형식(`templates/`)을 읽는다. 다른 파일을 읽거나 작업하기 전에 실행하고, 출력된 규칙을 따라 위키에 넣는다.

```bash
bash -c 'r="${XDG_CONFIG_HOME:-$HOME/.config}/gguk/home"; [ -z "${GGUK_HOME:-}" ] && [ -f "$r" ] && IFS= read -r GGUK_HOME < "$r"; s="${GGUK_HOME:-$HOME/gguk}/gguk-wiki/plugin/scripts/wiki-show.sh"; if [ -f "$s" ]; then bash "$s" "$@"; else echo "[GGUK 위키 규칙을 읽지 못함]"; echo; echo "위키 clone이 없습니다. README의 작업 공간 준비를 따라 위키를 clone하고 scripts/setup-workspace.sh를 실행하세요."; fi' _ AGENTS.md procedures/ingest.md domains.yml people.yml templates/decision.md templates/action-items.md templates/open-questions.md templates/note.md
```

- 출력 맨 위가 `[GGUK 위키 규칙을 읽지 못함]`이면 규칙 없이 진행하지 않는다. 다른 작업을 하지 말고 그 안내를 사용자에게 그대로 전한 뒤 멈춘다.
- 입력이 비어 있으면 대화에서 사용자가 넣어 달라고 한 내용을 입력으로 삼는다. 그것도 없으면 무엇을 넣을지 묻는다.
- push와 `gh pr create`는 규칙의 흐름 7번대로 업로더가 변경 요약과 확인 항목을 확인한 뒤에만 실행한다. 도구가 실행 전에 허락을 묻지 않아도 같다.
