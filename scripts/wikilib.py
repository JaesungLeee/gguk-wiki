"""위키 문서를 읽는 공통 함수. generate.py와 check.py가 함께 쓴다."""

from __future__ import annotations

import datetime as dt
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

DECISIONS_DIR = "wiki/decisions"
ACTION_ITEMS_DIR = "wiki/action-items"
OPEN_QUESTIONS_DIR = "wiki/open-questions"
DOMAIN_PAGES_DIR = "wiki/domains"
BASELINE_DIR = "raw/baseline"

# 기획서와 대응표. procedures/proposal.md를 따른다.
PROPOSAL_FILE = "proposal/project-proposal.md"
PROPOSAL_SOURCES = "proposal/sources.yml"

# 스크립트가 만드는 파일. PR에서 추가하거나 고치면 안 된다.
GENERATED_FILES = ("wiki/index.md", "wiki/log.md", "wiki/action-items.md")
GENERATED_DIRS = (DOMAIN_PAGES_DIR,)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# people.yml에 없는 사람 대신 쓰는 값. 목록 밖 사람의 이름은 위키에 남기지 않는다.
UNKNOWN_PERSON = "알 수 없음"
# 팀원이 맡지만 누구인지 정해지지 않은 몫. `assignee`에만 쓴다.
UNDECIDED_PERSON = "미정"


class FormatError(Exception):
    pass


@dataclass(frozen=True)
class Domain:
    name: str
    scope: str


@dataclass(frozen=True)
class Person:
    name: str
    github: str | None
    role: str


@dataclass(frozen=True)
class Repository:
    platform: str
    url: str

    @property
    def name(self) -> str:
        """레포 이름. url의 마지막 부분이고 작업 공간의 폴더 이름이 된다."""
        return self.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def nfc(text: str) -> str:
    """macOS(NFD)와 Linux(NFC)의 한글 파일 이름 차이를 없앤다."""
    return unicodedata.normalize("NFC", text)


def is_generated(rel_path: str) -> bool:
    rel_path = nfc(rel_path)
    return rel_path in GENERATED_FILES or any(rel_path.startswith(d + "/") for d in GENERATED_DIRS)


def load_domains(root: Path) -> list[Domain]:
    data = yaml.safe_load((root / "domains.yml").read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise FormatError("domains.yml: 목록이 아니다")
    domains = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("scope"):
            raise FormatError(f"domains.yml: {i + 1}번째 항목에 name과 scope가 필요하다")
        domains.append(Domain(str(entry["name"]), str(entry["scope"])))
    return domains


def load_people(root: Path) -> list[Person]:
    data = yaml.safe_load((root / "people.yml").read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise FormatError("people.yml: 목록이 아니다")
    people = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("role"):
            raise FormatError(f"people.yml: {i + 1}번째 항목에 name과 role이 필요하다")
        github = entry.get("github")
        people.append(Person(str(entry["name"]), str(github) if github else None, str(entry["role"])))
    return people


def load_repositories(root: Path) -> list[Repository]:
    data = yaml.safe_load((root / "platform-repository.yml").read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise FormatError("platform-repository.yml: 목록이 아니다")
    repos = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or not entry.get("platform") or not entry.get("url"):
            raise FormatError(f"platform-repository.yml: {i + 1}번째 항목에 platform과 url이 필요하다")
        repos.append(Repository(str(entry["platform"]), str(entry["url"])))
    return repos


def parse_frontmatter(path: Path) -> dict:
    return split_frontmatter(path.read_text(encoding="utf-8"))[0]


def split_frontmatter(text: str) -> tuple[dict, str]:
    """문서를 frontmatter와 본문으로 나눈다."""
    if not text.startswith("---\n"):
        raise FormatError("frontmatter가 없다")
    end = text.find("\n---", 4)
    if end == -1:
        raise FormatError("frontmatter가 닫히지 않았다")
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as e:
        raise FormatError(f"frontmatter를 읽을 수 없다: {e}") from e
    if not isinstance(data, dict):
        raise FormatError("frontmatter가 키-값 형식이 아니다")
    body = text[end + len("\n---"):]
    return data, body[body.find("\n") + 1:] if "\n" in body else ""


def date_str(value) -> str | None:
    """YAML이 날짜로 읽은 값과 문자열 날짜를 YYYY-MM-DD로 맞춘다. 날짜가 아니면 None."""
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, str) and DATE_RE.match(value):
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            return None
        return value
    return None


def list_docs(root: Path, subdir: str) -> list[tuple[str, Path]]:
    """subdir 아래 마크다운 파일을 (레포 기준 NFC 경로, 실제 경로)로 정렬해 돌려준다."""
    base = root / subdir
    if not base.is_dir():
        return []
    docs = [(nfc(p.relative_to(root).as_posix()), p) for p in base.rglob("*.md") if p.is_file()]
    return sorted(docs)


def repo_files(root: Path) -> set[str]:
    """레포 안의 모든 파일 경로(NFC). 문서가 가리키는 경로가 있는지 볼 때 쓴다."""
    files = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            rel = Path(dirpath, name).relative_to(root).as_posix()
            files.add(nfc(rel))
    return files


# 기획서 항목. `### [SCR-001] 이름` 같은 제목부터 같은 수준이거나 더 높은 수준의 다음 제목 전까지다.
# sdd-android(src/core/items.ts)와 같은 방식으로 나눠, Android가 가져간 뒤에도 바뀐 항목이 같게 계산되게 한다.
ITEM_ID = r"[A-Z]{1,5}-\d{3}"
ITEM_HEADING_RE = re.compile(rf"^\[({ITEM_ID})\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
RULE_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


@dataclass
class ItemSplit:
    items: dict[str, str]
    outside: str
    duplicates: list[str]


def normalize_text(text: str) -> str:
    """비교 전의 정규화. 줄 끝 공백과 끝의 빈 줄만 없앤다."""
    lines = [line.rstrip(" \t") for line in nfc(text.replace("\r\n", "\n")).split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def split_items(body: str) -> ItemSplit:
    """본문을 항목과 항목 밖으로 나눈다. 코드 블록 안의 제목은 제목으로 보지 않는다.

    항목 끝의 빈 줄과 구분선(`---`)은 항목 밖으로 친다. 장의 마지막 항목 뒤에 새 항목을 더해도
    앞 항목이 바뀐 것으로 계산되지 않게 하기 위해서다.
    """
    items: dict[str, str] = {}
    duplicates: list[str] = []
    outside: list[str] = []
    current: dict | None = None
    fence: str | None = None

    def close() -> None:
        lines = current["lines"]
        tail = []
        while lines and (lines[-1].strip() == "" or RULE_RE.match(lines[-1])):
            tail.insert(0, lines.pop())
        if current["id"] in items:
            duplicates.append(current["id"])
        else:
            items[current["id"]] = normalize_text("\n".join(lines))
        outside.extend(tail)

    for line in body.split("\n"):
        target = current["lines"] if current else outside
        if fence:
            if line.strip().startswith(fence):
                fence = None
            target.append(line)
            continue
        m = FENCE_RE.match(line)
        if m:
            fence = m.group(1)
            target.append(line)
            continue
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            item = ITEM_HEADING_RE.match(h.group(2).strip())
            if current and (level <= current["level"] or item):
                close()
                current = None
            if item:
                current = {"id": item.group(1), "level": level, "lines": [line]}
                continue
        (current["lines"] if current else outside).append(line)
    if current:
        close()
    return ItemSplit(items, normalize_text("\n".join(outside)), duplicates)
