#!/usr/bin/env bash
# GGUK 작업 공간 준비. docs/plugin.md의 "작업 공간"을 따른다.
#
#   git clone https://github.com/JaesungLeee/gguk-wiki.git ~/gguk/gguk-wiki
#   ~/gguk/gguk-wiki/scripts/setup-workspace.sh
#
# 코드 레포 3개를 GGUK_HOME(기본 ~/gguk) 아래에 clone한다. 이미 있으면 건너뛰므로 여러 번 실행해도 된다.
# Windows에서는 Git Bash에서 실행한다.

set -u

GGUK_HOME="${GGUK_HOME:-$HOME/gguk}"
CODE_REPOS=(Team-MINO-Node Team-MINO-Android Team-MINO-iOS)
GITHUB_ORG="https://github.com/mash-up-kr"

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*) is_windows=1 ;;
  *) is_windows=0 ;;
esac

if ! command -v git >/dev/null 2>&1; then
  echo "git이 없습니다. git을 설치한 뒤 다시 실행하세요. Windows는 Git for Windows를 설치합니다." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "안내: gh가 없습니다. 조회는 쓸 수 있고, ingest는 gh를 설치하고 'gh auth login' 후 쓸 수 있습니다."
elif ! gh auth status >/dev/null 2>&1; then
  echo "안내: gh에 로그인되어 있지 않습니다. 조회는 쓸 수 있고, ingest는 'gh auth login' 후 쓸 수 있습니다."
fi

mkdir -p "$GGUK_HOME" || { echo "$GGUK_HOME 폴더를 만들 수 없습니다." >&2; exit 1; }

results=()
for repo in "${CODE_REPOS[@]}"; do
  dest="$GGUK_HOME/$repo"
  if [ -d "$dest/.git" ]; then
    results+=("$repo: 이미 있음")
    continue
  fi
  if [ -e "$dest" ]; then
    # bash 3.2는 변수 바로 뒤의 한글을 변수 이름으로 읽으므로 중괄호로 감싼다.
    results+=("$repo: 실패 (${dest}가 이미 있지만 git 레포가 아닙니다)")
    continue
  fi

  echo "$repo clone 중..."
  clone_args=()
  if [ "$is_windows" = 1 ]; then
    clone_args=(-c core.longpaths=true)
  fi
  # macOS 기본 bash 3.2는 set -u에서 빈 배열을 펼치면 오류가 나므로 ${arr[@]+...} 형태로 쓴다.
  if error=$(git clone --quiet ${clone_args[@]+"${clone_args[@]}"} "$GITHUB_ORG/$repo.git" "$dest" 2>&1); then
    results+=("$repo: clone 완료")
  else
    results+=("$repo: 실패 (${error##*$'\n'})")
  fi
done

if [ -d "$GGUK_HOME/gguk-wiki/.git" ]; then
  results+=("gguk-wiki: 있음")
else
  results+=("gguk-wiki: 없음 ($GGUK_HOME/gguk-wiki에 clone하세요)")
fi

echo
echo "작업 공간: $GGUK_HOME"
failed=0
for line in "${results[@]}"; do
  echo "  $line"
  case "$line" in *": 실패"* | *": 없음"*) failed=1 ;; esac
done

exit "$failed"
