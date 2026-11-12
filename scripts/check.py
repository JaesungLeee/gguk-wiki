"""위키 문서 형식 검사. 검사 항목은 docs/ingest.md의 "형식 검사는 PR에서 막는다"를 따른다.

    python scripts/check.py                  # 레포 전체 문서 검사
    python scripts/check.py --base origin/main  # PR 변경(raw/ 수정·삭제, 생성 파일 추가·수정)도 검사
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

import wikilib
from wikilib import FormatError, nfc

DOMAIN_NAME_RE = re.compile(r"^[a-z]+(-[a-z]+)*$")
DATED_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-.+\.md$")

DECISION_REQUIRED = ("title", "status", "decided_at", "domains", "platforms", "source", "durability")
DECISION_OPTIONAL = ("supersedes", "superseded_by")
DECISION_STATUS = ("decided", "superseded")
DURABILITY = ("permanent", "temporal")
PLATFORMS = ("server", "android", "ios", "design")

ACTION_REQUIRED = ("source", "items")
ACTION_ITEM_REQUIRED = ("task", "status")
ACTION_STATUS = ("open", "done", "dropped")

OPEN_QUESTION_REQUIRED = ("source", "items")
OPEN_QUESTION_ITEM_REQUIRED = ("question", "domains", "status")
OPEN_QUESTION_STATUS = ("open", "resolved", "dropped")


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.errors: list[str] = []
        self.files = wikilib.repo_files(root)
        self.domain_names = {d.name for d in wikilib.load_domains(root)}
        # 결정 경로 → frontmatter. 대체 관계를 양쪽에서 맞춰 볼 때 쓴다.
        self.decisions: dict[str, dict] = {}

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    # 공통 검사

    def present(self, where: str, data: dict, key: str) -> bool:
        """필드가 있으면 값이 비어 있지 않은지 본다. 값이 없는 선택 필드는 줄을 빼야 한다."""
        if key not in data:
            return False
        if data[key] is None or data[key] == "" or data[key] == []:
            self.error(where, f"`{key}` 값이 비어 있다. 값이 없으면 줄을 뺀다")
            return False
        return True

    def require(self, where: str, data: dict, keys: tuple[str, ...]) -> None:
        for key in keys:
            if key not in data:
                self.error(where, f"필수 필드 `{key}`가 없다")

    def one_of(self, where: str, key: str, value, allowed: tuple[str, ...]) -> None:
        if value not in allowed:
            self.error(where, f"`{key}` 값 `{value}`는 {' | '.join(allowed)} 중 하나여야 한다")

    def path_exists(self, where: str, key: str, value) -> None:
        if not isinstance(value, str) or nfc(value) not in self.files:
            self.error(where, f"`{key}`가 가리키는 파일 `{value}`가 없다")

    def domains(self, where: str, value, required: bool) -> None:
        if not isinstance(value, list):
            self.error(where, "`domains`는 목록이어야 한다")
            return
        if required and not value:
            self.error(where, "`domains`가 1개 이상 있어야 한다")
        for name in value:
            if name not in self.domain_names:
                self.error(where, f"도메인 `{name}`이 domains.yml에 없다")

    def mirrors_source(self, rel: str, data: dict, subdir: str) -> None:
        """액션 아이템·미결 파일의 경로가 원본의 raw/ 아래 경로를 따르는지 본다."""
        source = data.get("source")
        if not isinstance(source, str) or not nfc(source).startswith("raw/"):
            return
        expected = posixpath.join(subdir, nfc(source)[len("raw/"):])
        if rel != expected:
            self.error(rel, f"경로는 원본 경로를 따라 `{expected}`여야 한다")

    def load(self, rel: str, path: Path) -> dict | None:
        try:
            return wikilib.parse_frontmatter(path)
        except FormatError as e:
            self.error(rel, str(e))
            return None

    # 문서 종류별 검사

    def check_decision(self, rel: str, path: Path) -> None:
        data = self.load(rel, path)
        if data is None:
            return
        self.decisions[rel] = data
        self.require(rel, data, DECISION_REQUIRED)
        if self.present(rel, data, "title") and not isinstance(data["title"], str):
            self.error(rel, "`title`은 문자열이어야 한다")
        if self.present(rel, data, "status"):
            self.one_of(rel, "status", data["status"], DECISION_STATUS)
        if self.present(rel, data, "decided_at"):
            decided_at = wikilib.date_str(data["decided_at"])
            if decided_at is None:
                self.error(rel, "`decided_at`은 YYYY-MM-DD 날짜여야 한다")
            else:
                m = DATED_FILE_RE.match(posixpath.basename(rel))
                if not m:
                    self.error(rel, "파일 이름은 `YYYY-MM-DD-제목.md`여야 한다")
                elif m.group(1) != decided_at:
                    self.error(rel, f"파일 이름의 날짜 {m.group(1)}가 `decided_at` {decided_at}와 다르다")
        if "domains" in data:
            self.domains(rel, data["domains"], required=True)
        if "platforms" in data:
            platforms = data["platforms"]
            if not isinstance(platforms, list):
                self.error(rel, "`platforms`는 목록이어야 한다")
            else:
                if not platforms:
                    self.error(rel, "`platforms`가 1개 이상 있어야 한다. 하지 않기로 한 결정은 해당 직무를 모두 적는다")
                for p in platforms:
                    self.one_of(rel, "platforms", p, PLATFORMS)
        if self.present(rel, data, "source"):
            self.path_exists(rel, "source", data["source"])
        if self.present(rel, data, "durability"):
            self.one_of(rel, "durability", data["durability"], DURABILITY)
        for key in DECISION_OPTIONAL:
            if self.present(rel, data, key):
                self.path_exists(rel, key, data[key])

    def check_supersede_links(self) -> None:
        """대체 표시가 양쪽에서 짝이 맞는지 본다. 반만 처리하면 옛 결정이 유효한 것으로 남는다."""
        for rel, data in self.decisions.items():
            status = data.get("status")
            new = data.get("superseded_by")
            old = data.get("supersedes")
            if status == "superseded" and not new:
                self.error(rel, "`superseded`이면 `superseded_by`가 있어야 한다")
            if new and status != "superseded":
                self.error(rel, "`superseded_by`가 있으면 `status`가 `superseded`여야 한다")
            if isinstance(new, str) and nfc(new) in self.decisions:
                if nfc(str(self.decisions[nfc(new)].get("supersedes") or "")) != rel:
                    self.error(rel, f"이 결정을 대체한 `{new}`의 `supersedes`가 이 결정을 가리키지 않는다")
            if isinstance(old, str) and nfc(old) in self.decisions:
                if nfc(str(self.decisions[nfc(old)].get("superseded_by") or "")) != rel:
                    self.error(rel, f"이 결정이 대체한 `{old}`의 `superseded_by`가 이 결정을 가리키지 않는다")

    def items(self, rel: str, data: dict) -> list[tuple[str, dict]]:
        items = data.get("items")
        if not isinstance(items, list) or not items:
            if "items" in data:
                self.error(rel, "`items`는 항목이 1개 이상인 목록이어야 한다")
            return []
        result = []
        for i, item in enumerate(items, start=1):
            where = f"{rel} items[{i}]"
            if not isinstance(item, dict):
                self.error(where, "항목은 키-값 형식이어야 한다")
                continue
            result.append((where, item))
        return result

    def check_action_items(self, rel: str, path: Path) -> None:
        data = self.load(rel, path)
        if data is None:
            return
        self.require(rel, data, ACTION_REQUIRED)
        if self.present(rel, data, "source"):
            self.path_exists(rel, "source", data["source"])
            self.mirrors_source(rel, data, wikilib.ACTION_ITEMS_DIR)
        if "domains" in data:
            self.domains(rel, data["domains"], required=False)
        for where, item in self.items(rel, data):
            self.require(where, item, ACTION_ITEM_REQUIRED)
            for key in ("task", "assignee"):
                self.present(where, item, key)
            if self.present(where, item, "status"):
                self.one_of(where, "status", item["status"], ACTION_STATUS)
            if self.present(where, item, "due") and wikilib.date_str(item["due"]) is None:
                self.error(where, "`due`는 YYYY-MM-DD 날짜여야 한다")

    def check_open_questions(self, rel: str, path: Path) -> None:
        data = self.load(rel, path)
        if data is None:
            return
        self.require(rel, data, OPEN_QUESTION_REQUIRED)
        if self.present(rel, data, "source"):
            self.path_exists(rel, "source", data["source"])
            self.mirrors_source(rel, data, wikilib.OPEN_QUESTIONS_DIR)
        for where, item in self.items(rel, data):
            self.require(where, item, OPEN_QUESTION_ITEM_REQUIRED)
            self.present(where, item, "question")
            if "domains" in item:
                self.domains(where, item["domains"], required=True)
            if self.present(where, item, "status"):
                self.one_of(where, "status", item["status"], OPEN_QUESTION_STATUS)
            if item.get("status") == "resolved":
                if "resolved_by" not in item:
                    self.error(where, "`resolved`이면 `resolved_by`가 있어야 한다")
                elif self.present(where, item, "resolved_by"):
                    self.path_exists(where, "resolved_by", item["resolved_by"])
            elif "resolved_by" in item:
                self.error(where, "`resolved_by`는 `resolved`일 때만 쓴다")

    def check_domains_file(self) -> None:
        seen = set()
        for domain in wikilib.load_domains(self.root):
            if not DOMAIN_NAME_RE.match(domain.name):
                self.error("domains.yml", f"도메인 이름 `{domain.name}`은 영어 소문자와 하이픈으로 쓴다")
            if domain.name in seen:
                self.error("domains.yml", f"도메인 `{domain.name}`이 두 번 있다")
            seen.add(domain.name)

    def check_docs(self) -> None:
        self.check_domains_file()
        for rel, path in wikilib.list_docs(self.root, wikilib.DECISIONS_DIR):
            self.check_decision(rel, path)
        self.check_supersede_links()
        for rel, path in wikilib.list_docs(self.root, wikilib.ACTION_ITEMS_DIR):
            self.check_action_items(rel, path)
        for rel, path in wikilib.list_docs(self.root, wikilib.OPEN_QUESTIONS_DIR):
            self.check_open_questions(rel, path)

    # PR 변경 검사

    def check_changes(self, base: str) -> None:
        out = subprocess.run(
            ["git", "-C", str(self.root), "diff", "--name-status", "--no-renames", "-z", f"{base}...HEAD"],
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        fields = [f for f in out.split("\0") if f]
        for status, rel in zip(fields[0::2], fields[1::2]):
            rel = nfc(rel)
            if rel.startswith("raw/") and status in ("M", "D", "T"):
                action = "지웠다" if status == "D" else "고쳤다"
                self.error(rel, f"raw/의 기존 파일을 {action}. 원본은 넣은 뒤 고치거나 지우지 않는다")
            if wikilib.is_generated(rel) and status in ("A", "M", "T"):
                self.error(rel, "생성 파일을 추가하거나 고쳤다. merge 뒤 CI가 다시 만든다")


def main() -> int:
    parser = argparse.ArgumentParser(description="위키 문서 형식 검사")
    parser.add_argument("--root", type=Path, default=wikilib.REPO_ROOT)
    parser.add_argument("--base", help="PR의 base ref. 주면 raw/와 생성 파일 변경도 검사한다")
    args = parser.parse_args()

    try:
        checker = Checker(args.root.resolve())
    except FormatError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    checker.check_docs()
    if args.base:
        checker.check_changes(args.base)

    for message in checker.errors:
        print(f"error: {message}", file=sys.stderr)
    if checker.errors:
        print(f"\n형식 검사 실패: {len(checker.errors)}건", file=sys.stderr)
        return 1
    print("형식 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
