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

# 스크립트가 만드는 파일. PR에서 추가하거나 고치면 안 된다.
GENERATED_FILES = ("wiki/index.md", "wiki/log.md", "wiki/action-items.md")
GENERATED_DIRS = (DOMAIN_PAGES_DIR,)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class FormatError(Exception):
    pass


@dataclass(frozen=True)
class Domain:
    name: str
    scope: str


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


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
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
    return data


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
