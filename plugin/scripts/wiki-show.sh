#!/usr/bin/env bash
# GGUK 위키 규칙 파일을 위키 clone의 default 브랜치(origin/HEAD)에서 읽어 출력한다.
# ingest·ask 스킬이 SKILL.md의 !`...` 주입으로 부른다. docs/plugin.md의 "구성"을 따른다.
#
#   wiki-show.sh AGENTS.md procedures/ask.md
#
# 읽지 못해도 안내를 출력하고 0으로 끝낸다. 0이 아니면 Claude Code가 스킬 호출을 중단해 안내가 전달되지 않는다.

set -u

# 작업 공간: GGUK_HOME 환경 변수, 설정 스크립트(setup-workspace.sh)가 기록한 위치, ~/gguk 순으로 정한다.
home_record="${XDG_CONFIG_HOME:-$HOME/.config}/gguk/home"
if [ -z "${GGUK_HOME:-}" ] && [ -f "$home_record" ]; then
  IFS= read -r GGUK_HOME < "$home_record"
fi
GGUK_HOME="${GGUK_HOME:-$HOME/gguk}"
wiki="$GGUK_HOME/gguk-wiki"

# 안내에 보여 줄 경로. 홈 아래면 ~로 줄인다. 명령 예시(cmd_path)는 공백이 있으면 전체 경로를 따옴표로 감싼다.
case "$wiki" in
  "$HOME"/*) shown="~${wiki#"$HOME"}" ;;
  *) shown="$wiki" ;;
esac
case "$shown" in
  *" "*) cmd_path="\"$wiki\"" ;;
  *) cmd_path="$shown" ;;
esac

# 규칙을 읽지 못했을 때. 스킬 본문은 이 첫 줄을 보면 안내만 전하고 멈추라고 지시한다.
fail() {
  echo "[GGUK 위키 규칙을 읽지 못함]"
  echo
  echo "$1"
  echo
  echo "$2"
  exit 0
}

if ! command -v git >/dev/null 2>&1; then
  fail "git이 없습니다." "git을 설치한 뒤 다시 실행하세요. Windows는 Git for Windows를 설치합니다."
fi
if [ ! -d "$wiki/.git" ]; then
  fail "위키 clone이 없습니다: $shown" "작업 공간을 준비한 뒤 다시 실행하세요. Windows에서는 Git Bash에서 실행합니다.

    git clone https://github.com/JaesungLeee/gguk-wiki.git $cmd_path
    $cmd_path/scripts/setup-workspace.sh

다른 폴더에 두려면 위 두 명령의 경로를 그 폴더로 바꿔 실행합니다. 설정 스크립트가 위치를 기록하므로 따로 설정할 것은 없습니다."
fi

# 최신 규칙을 읽기 위해 먼저 fetch한다. 오프라인이면 마지막으로 받은 상태를 읽는다.
# 전송이 5초 동안 초당 1KB 아래로 떨어지면 멈춘다.
if git -C "$wiki" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=5 fetch --quiet origin 2>/dev/null; then
  fetched="방금 fetch함"
else
  fetched="fetch 실패, 마지막으로 받은 상태"
fi

if ! head=$(git -C "$wiki" rev-parse --abbrev-ref origin/HEAD 2>/dev/null); then
  fail "위키 clone에 origin/HEAD가 없습니다: $shown" "아래 명령으로 default 브랜치를 설정한 뒤 다시 실행하세요.

    git -C $cmd_path remote set-head origin --auto"
fi
head="${head#origin/}"
sha=$(git -C "$wiki" rev-parse --short origin/HEAD)

for file in "$@"; do
  if ! git -C "$wiki" cat-file -e "origin/HEAD:$file" 2>/dev/null; then
    fail "위키 default 브랜치(${head} @ ${sha})에 \`$file\` 파일이 없습니다." "위키 레포 관리자에게 알려 주세요."
  fi
done

echo "<!-- GGUK 위키 규칙: ${head} @ ${sha} (${fetched}) -->"
echo "<!-- 작업 공간: $GGUK_HOME (규칙의 ~/gguk은 이 경로를 뜻한다) -->"
for file in "$@"; do
  echo
  echo "<!-- 파일: $file -->"
  git -C "$wiki" show "origin/HEAD:$file"
done
