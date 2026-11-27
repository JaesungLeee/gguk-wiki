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

DECISION_REQUIRED = ("title", "status", "kind", "decided_at", "domains", "platforms", "source", "durability")
DECISION_STATUS = ("decided", "superseded")
DURABILITY = ("permanent", "temporal")
PLATFORMS = ("server", "android", "ios", "design")
KINDS = ("product", "tech")
# platform-repository.yml의 url. 레포 이름(마지막 부분)이 작업 공간의 폴더 이름이 된다
REPOSITORY_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

ACTION_REQUIRED = ("source", "items")
ACTION_ITEM_REQUIRED = ("task", "status")
# 새로 추가하거나 고친 파일의 필수 필드. 담당자 목록 규칙 전에 들어간 파일은 `assignee`가 없거나 문자열일 수 있다
NEW_ACTION_ITEM_REQUIRED = ("task", "assignee", "status")
ACTION_STATUS = ("open", "done", "dropped")

OPEN_QUESTION_REQUIRED = ("source", "items")
OPEN_QUESTION_ITEM_REQUIRED = ("question", "domains", "kind", "status")
OPEN_QUESTION_STATUS = ("open", "resolved", "dropped")


def supersedes_list(value) -> list:
    """`supersedes`는 경로 하나(문자열)나 경로 목록이다. 비교할 수 있게 NFC 경로 목록으로 맞춘다."""
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [nfc(v) if isinstance(v, str) else v for v in values]


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.errors: list[str] = []
        self.files = wikilib.repo_files(root)
        self.domain_names = {d.name for d in wikilib.load_domains(root)}
        self.people = wikilib.load_people(root)
        self.person_names = {p.name for p in self.people}
        self.repositories = wikilib.load_repositories(root)
        # `tech` 결정은 코드 레포가 있는 플랫폼 2개 이상에 걸친다. 하나뿐이면 그 레포에서 관리하는 플랫폼 내부 결정이다
        self.code_platforms = sorted({r.platform for r in self.repositories})
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

    def decision_path(self, where: str, key: str, value) -> None:
        """대체·해소 관계는 결정 문서만 가리킨다. 다른 파일을 가리키면 대신할 결정 없이 결정·미결이 도메인 페이지에서 빠진다."""
        if isinstance(value, str) and not (
            nfc(value).startswith(wikilib.DECISIONS_DIR + "/") and value.endswith(".md")
        ):
            self.error(where, f"`{key}`는 `{wikilib.DECISIONS_DIR}/` 아래 결정 문서를 가리켜야 한다")
            return
        self.path_exists(where, key, value)

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
        if self.present(rel, data, "kind"):
            self.one_of(rel, "kind", data["kind"], KINDS)
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
                if data.get("kind") == "tech" and len(set(platforms) & set(self.code_platforms)) < 2:
                    self.error(rel, f"`tech` 결정은 `platforms`에 {', '.join(self.code_platforms)} 중 2개 이상이 있어야 한다. 한 플랫폼 안의 결정은 그 레포에서 관리한다")
        if self.present(rel, data, "source"):
            self.path_exists(rel, "source", data["source"])
        if self.present(rel, data, "durability"):
            self.one_of(rel, "durability", data["durability"], DURABILITY)
        if self.present(rel, data, "supersedes"):
            seen = []
            for old in supersedes_list(data["supersedes"]):
                if old in seen:
                    self.error(rel, f"`supersedes`에 `{old}`가 두 번 있다")
                    continue
                seen.append(old)
                self.decision_path(rel, "supersedes", old)
        if self.present(rel, data, "superseded_by"):
            if isinstance(data["superseded_by"], list):
                self.error(rel, "`superseded_by`는 경로 하나여야 한다. 결정 하나를 여러 결정으로 나눠 대체하지 않는다")
            else:
                self.decision_path(rel, "superseded_by", data["superseded_by"])

    def check_supersede_links(self) -> None:
        """대체 표시가 양쪽에서 짝이 맞는지 본다. 반만 처리하면 옛 결정이 유효한 것으로 남는다.

        새 결정은 `supersedes`로 여러 결정을 대체할 수 있지만, 이전 결정은 `superseded_by`로 한 결정만 가리킨다.
        """
        for rel, data in self.decisions.items():
            status = data.get("status")
            new = data.get("superseded_by")
            if status == "superseded" and not new:
                self.error(rel, "`superseded`이면 `superseded_by`가 있어야 한다")
            if new and status != "superseded":
                self.error(rel, "`superseded_by`가 있으면 `status`가 `superseded`여야 한다")
            if isinstance(new, str) and nfc(new) in self.decisions:
                if rel not in supersedes_list(self.decisions[nfc(new)].get("supersedes")):
                    self.error(rel, f"이 결정을 대체한 `{new}`의 `supersedes`에 이 결정이 없다")
            for old in supersedes_list(data.get("supersedes")):
                if isinstance(old, str) and old in self.decisions:
                    if nfc(str(self.decisions[old].get("superseded_by") or "")) != rel:
                        self.error(rel, f"이 결정이 대체한 `{old}`의 `superseded_by`가 이 결정을 가리키지 않는다")

    def check_supersede_cycles(self) -> None:
        """대체가 돌면 짝이 맞아도 사슬에 `decided` 결정이 없어 그 주제가 도메인 페이지에서 사라진다."""
        reported: set[str] = set()
        for start in self.decisions:
            chain: list[str] = []
            rel = start
            while rel in self.decisions and rel not in chain:
                chain.append(rel)
                new = self.decisions[rel].get("superseded_by")
                rel = nfc(new) if isinstance(new, str) else None
            if rel not in chain or rel in reported:
                continue
            cycle = chain[chain.index(rel):]
            reported.update(cycle)
            first = cycle.index(min(cycle))
            cycle = cycle[first:] + cycle[:first]
            self.error(cycle[0], "대체 관계가 순환한다: " + " → ".join(cycle + [cycle[0]]))

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
            self.present(where, item, "task")
            # 담당자는 check_new_action_items만 본다. 여기서도 보면 빈 목록에 "줄을 뺀다"가 함께 나와 필수 규칙과 어긋난다
            if self.present(where, item, "status"):
                self.one_of(where, "status", item["status"], ACTION_STATUS)
            if self.present(where, item, "due") and wikilib.date_str(item["due"]) is None:
                self.error(where, "`due`는 YYYY-MM-DD 날짜여야 한다")

    def assignee(self, where: str, value) -> None:
        """담당자는 맡은 사람 목록이다. 목록 밖 사람은 이름 대신 "알 수 없음", 정해지지 않은 몫은 "미정"으로 쓴다."""
        if not isinstance(value, list) or not value:
            self.error(where, f"`assignee`는 1명 이상인 목록이어야 한다. 정해지지 않았으면 `[{wikilib.UNDECIDED_PERSON}]`으로 쓴다")
            return
        allowed = self.person_names | {wikilib.UNKNOWN_PERSON, wikilib.UNDECIDED_PERSON}
        seen = []
        for name in value:
            if name in seen:
                self.error(where, f"`assignee`에 `{name}`이 두 번 있다")
                continue
            seen.append(name)
            if not isinstance(name, str) or name not in allowed:
                self.error(where, f"`assignee` 값 `{name}`이 people.yml에 없다. 목록에 없는 사람은 `{wikilib.UNKNOWN_PERSON}`으로 쓴다")

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
            if self.present(where, item, "kind"):
                self.one_of(where, "kind", item["kind"], KINDS)
            if self.present(where, item, "status"):
                self.one_of(where, "status", item["status"], OPEN_QUESTION_STATUS)
            if item.get("status") == "resolved":
                if "resolved_by" not in item:
                    self.error(where, "`resolved`이면 `resolved_by`가 있어야 한다")
                elif self.present(where, item, "resolved_by"):
                    self.decision_path(where, "resolved_by", item["resolved_by"])
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

    def check_people_file(self) -> None:
        names, accounts = set(), set()
        for person in self.people:
            self.one_of("people.yml", "role", person.role, PLATFORMS)
            if person.name in (wikilib.UNKNOWN_PERSON, wikilib.UNDECIDED_PERSON):
                self.error("people.yml", f"`{person.name}`은 이름으로 쓸 수 없다. 목록 밖 사람과 정해지지 않은 담당자에 쓰는 값이다")
            if person.name in names:
                self.error("people.yml", f"이름 `{person.name}`이 두 번 있다")
            names.add(person.name)
            if person.github:
                if person.github.lower() in accounts:
                    self.error("people.yml", f"GitHub 아이디 `{person.github}`가 두 번 있다")
                accounts.add(person.github.lower())

    def check_repositories_file(self) -> None:
        where = "platform-repository.yml"
        platforms, names = set(), set()
        for repo in self.repositories:
            if repo.platform == "design" or repo.platform not in PLATFORMS:
                self.error(where, f"`platform` 값 `{repo.platform}`은 {', '.join(p for p in PLATFORMS if p != 'design')} 중 하나여야 한다")
            if repo.platform in platforms:
                self.error(where, f"플랫폼 `{repo.platform}`이 두 번 있다. 플랫폼마다 레포 하나다")
            platforms.add(repo.platform)
            if not REPOSITORY_URL_RE.match(repo.url):
                self.error(where, f"`url` `{repo.url}`은 `https://github.com/<조직>/<레포>` 형식이어야 한다")
            elif repo.name.lower() in names:
                self.error(where, f"레포 이름 `{repo.name}`이 두 번 있다. 작업 공간의 폴더 이름이 겹친다")
            names.add(repo.name.lower())

    def check_docs(self) -> None:
        self.check_domains_file()
        self.check_people_file()
        self.check_repositories_file()
        for rel, path in wikilib.list_docs(self.root, wikilib.DECISIONS_DIR):
            self.check_decision(rel, path)
        self.check_supersede_links()
        self.check_supersede_cycles()
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
        for status, raw_rel in zip(fields[0::2], fields[1::2]):
            rel = nfc(raw_rel)
            # `.gitkeep`은 빈 폴더를 남기는 자리표시자라 원본이 아니다. 폴더 구조를 바꿀 때 지울 수 있다
            if rel.startswith("raw/") and posixpath.basename(rel) != ".gitkeep" and status in ("M", "D", "T"):
                action = "지웠다" if status == "D" else "고쳤다"
                self.error(rel, f"raw/의 기존 파일을 {action}. 원본은 넣은 뒤 고치거나 지우지 않는다")
            if wikilib.is_generated(rel) and status in ("A", "M", "T"):
                self.error(rel, "생성 파일을 추가하거나 고쳤다. merge 뒤 CI가 다시 만든다")
            if rel.startswith("raw/notes/") and rel.endswith(".md") and status == "A":
                self.check_note(rel, self.root / raw_rel)
            if rel.startswith(wikilib.ACTION_ITEMS_DIR + "/") and rel.endswith(".md") and status in ("A", "M"):
                self.check_new_action_items(rel, self.root / raw_rel)

    def check_note(self, rel: str, path: Path) -> None:
        """새로 추가한 채팅 원본에 말한 사람이 있는지 본다. 기존 원본은 고칠 수 없으므로 검사하지 않는다."""
        data = self.load(rel, path)
        if data is None:
            return
        author = data.get("author")
        if not author:
            self.error(rel, "`author`가 없거나 비어 있다. 말한 사람을 적는다")
        elif not isinstance(author, str) or author not in self.person_names | {wikilib.UNKNOWN_PERSON}:
            self.error(rel, f"`author` 값 `{author}`가 people.yml에 없다. 말한 사람 한 명의 name이나 `{wikilib.UNKNOWN_PERSON}`을 적는다")


    def check_new_action_items(self, rel: str, path: Path) -> None:
        """새로 추가하거나 고친 액션 아이템의 담당자를 본다. 이 규칙 전에 들어간 파일은 형식이 달라 PR에서 바뀌지 않으면 검사하지 않고, 고치면 모든 항목을 새 형식으로 본다.

        frontmatter와 항목 형식 오류는 check_docs가 이미 내므로 여기서는 담당자만 본다.
        """
        try:
            data = wikilib.parse_frontmatter(path)
        except FormatError:
            return
        items = data.get("items")
        if not isinstance(items, list):
            return
        for i, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            where = f"{rel} items[{i}]"
            if "assignee" not in item:
                self.error(where, f"필수 필드 `assignee`가 없다. 정해지지 않았으면 `[{wikilib.UNDECIDED_PERSON}]`으로 쓴다")
            else:
                self.assignee(where, item["assignee"])


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
