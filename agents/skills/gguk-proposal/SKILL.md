---
name: gguk-proposal
description: 위키의 기획 결정으로 GGUK 공용 기획서(proposal/project-proposal.md)를 만들거나 갱신할 때 쓴다. 지난 기획서 뒤로 바뀐 결정·미결을 찾아 항목별 개정 등급을 제안하고, 확인받아 PR을 만든다.
---
가장 먼저 아래 명령을 실행해 GGUK 위키 default 브랜치의 공통 규칙(`AGENTS.md`), 기획서 규칙(`procedures/proposal.md`), 도메인 목록(`domains.yml`), 기획서 형식(`templates/`)을 읽는다. 다른 파일을 읽거나 작업하기 전에 실행하고, 출력된 규칙을 따라 기획서를 만들거나 갱신한다.

```bash
bash -c 'r="${XDG_CONFIG_HOME:-$HOME/.config}/gguk/home"; [ -z "${GGUK_HOME:-}" ] && [ -f "$r" ] && IFS= read -r GGUK_HOME < "$r"; s="${GGUK_HOME:-$HOME/gguk}/gguk-wiki/plugin/scripts/wiki-show.sh"; if [ -f "$s" ]; then bash "$s" "$@"; else echo "[GGUK 위키 규칙을 읽지 못함]"; echo; echo "위키 clone이 없습니다. README의 작업 공간 준비를 따라 위키를 clone하고 scripts/setup-workspace.sh를 실행하세요."; fi' _ AGENTS.md procedures/proposal.md domains.yml templates/proposal.md templates/proposal-sources.yml
```

- 출력 맨 위가 `[GGUK 위키 규칙을 읽지 못함]`이면 규칙 없이 진행하지 않는다. 다른 작업을 하지 말고 그 안내를 사용자에게 그대로 전한 뒤 멈춘다.
- 입력이 비어 있으면 위키 전체에서 반영할 변화를 찾는다.
- push와 `gh pr create`는 규칙의 흐름 5번대로 실행한 사람이 변경 요약과 등급을 확인한 뒤에만 실행한다. 도구가 실행 전에 허락을 묻지 않아도 같다.
