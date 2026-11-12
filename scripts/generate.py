"""생성 파일을 만든다. 내용은 docs/ingest.md의 "생성 파일은 스크립트가 만든다"를 따른다.

    python scripts/generate.py            # wiki/domains/, index.md, log.md, action-items.md를 다시 쓴다
    python scripts/generate.py --dry-run  # 쓰지 않고 만들 수 있는지만 확인한다

같은 입력이면 항상 같은 결과가 나와야 하므로 파일 내용만 읽는다. git 이력이나 오늘 날짜는 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path

import wikilib
from wikilib import Domain

HEADER = "<!-- 자동 생성 파일. 직접 수정하지 않는다. scripts/generate.py가 만든다. -->\n"


@dataclass(frozen=True)
class Decision:
    path: str
    title: str
    status: str
    decided_at: str
    domains: tuple[str, ...]
    platforms: tuple[str, ...]
    superseded_by: str | None


@dataclass(frozen=True)
class OpenQuestion:
    question: str
    domains: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class ActionItem:
    task: str
    assignee: str
    due: str | None
    source: str


def cell(text) -> str:
    """표 칸에 넣을 수 있게 줄바꿈과 `|`를 바꾼다."""
    return " ".join(str(text).split()).replace("|", "\\|")


def link(text: str, target: str, from_dir: str) -> str:
    return f"[{cell(text)}]({posixpath.relpath(target, from_dir)})"


def load_decisions(root: Path) -> list[Decision]:
    decisions = []
    for rel, path in wikilib.list_docs(root, wikilib.DECISIONS_DIR):
        data = wikilib.parse_frontmatter(path)
        decisions.append(
            Decision(
                path=rel,
                title=str(data["title"]),
                status=data["status"],
                decided_at=wikilib.date_str(data["decided_at"]),
                domains=tuple(data["domains"]),
                platforms=tuple(data.get("platforms") or ()),
                superseded_by=data.get("superseded_by"),
            )
        )
    # 결정일 최신순. 같은 날이면 경로순으로 고정한다.
    decisions.sort(key=lambda d: d.path)
    decisions.sort(key=lambda d: d.decided_at, reverse=True)
    return decisions


def load_open_questions(root: Path) -> list[OpenQuestion]:
    questions = []
    for _, path in wikilib.list_docs(root, wikilib.OPEN_QUESTIONS_DIR):
        data = wikilib.parse_frontmatter(path)
        for item in data["items"]:
            if item["status"] == "open":
                questions.append(OpenQuestion(str(item["question"]), tuple(item["domains"]), data["source"]))
    return questions


def load_action_items(root: Path) -> list[ActionItem]:
    items = []
    for _, path in wikilib.list_docs(root, wikilib.ACTION_ITEMS_DIR):
        data = wikilib.parse_frontmatter(path)
        for item in data["items"]:
            if item["status"] == "open":
                due = wikilib.date_str(item["due"]) if "due" in item else None
                items.append(ActionItem(str(item["task"]), str(item["assignee"]), due, data["source"]))
    # 기한순, 기한 없는 항목은 맨 뒤. 정렬이 안정적이므로 같은 기한은 원본 경로순을 유지한다.
    items.sort(key=lambda a: (a.due is None, a.due or ""))
    return items


def domain_page(domain: Domain, decisions: list[Decision], questions: list[OpenQuestion]) -> str:
    here = wikilib.DOMAIN_PAGES_DIR
    lines = [HEADER, f"# {domain.name}\n", f"{domain.scope}\n", f"## 결정 ({len(decisions)})\n"]
    if decisions:
        lines.append("| 결정 | 결정일 | 플랫폼 |")
        lines.append("| --- | --- | --- |")
        for d in decisions:
            lines.append(f"| {link(d.title, d.path, here)} | {d.decided_at} | {cell(', '.join(d.platforms))} |")
        lines.append("")
    else:
        lines.append("없음\n")
    lines.append(f"## 미결 ({len(questions)})\n")
    if questions:
        for q in questions:
            lines.append(f"- {cell(q.question)} ({link('원본', q.source, here)})")
        lines.append("")
    else:
        lines.append("없음\n")
    return "\n".join(lines)


def index_page(domains: list[Domain], counts: dict[str, tuple[int, int]]) -> str:
    lines = [HEADER, "# GGUK 위키 목차\n", "| 도메인 | 범위 | 결정 | 미결 |", "| --- | --- | --- | --- |"]
    for domain in domains:
        decided, open_count = counts[domain.name]
        page = f"{wikilib.DOMAIN_PAGES_DIR}/{domain.name}.md"
        lines.append(f"| {link(domain.name, page, 'wiki')} | {cell(domain.scope)} | {decided} | {open_count} |")
    return "\n".join(lines) + "\n"


def log_page(decisions: list[Decision]) -> str:
    by_path = {d.path: d for d in decisions}
    lines = [HEADER, "# 결정 기록\n", "결정일 최신순이다.\n"]
    if not decisions:
        lines.append("없음")
        return "\n".join(lines) + "\n"
    lines += ["| 결정일 | 결정 | 도메인 | 상태 |", "| --- | --- | --- | --- |"]
    for d in decisions:
        if d.status == "superseded":
            new = by_path.get(wikilib.nfc(d.superseded_by or ""))
            state = f"대체됨 → {link(new.title, new.path, 'wiki')}" if new else "대체됨"
        else:
            state = "유효"
        lines.append(f"| {d.decided_at} | {link(d.title, d.path, 'wiki')} | {cell(', '.join(d.domains))} | {state} |")
    return "\n".join(lines) + "\n"


def action_items_page(items: list[ActionItem]) -> str:
    lines = [HEADER, "# 열린 액션 아이템\n", "기한순이다. 기한이 지났는지는 조회할 때 판단한다.\n"]
    if not items:
        lines.append("없음")
        return "\n".join(lines) + "\n"
    lines += ["| 기한 | 할 일 | 담당자 | 원본 |", "| --- | --- | --- | --- |"]
    for a in items:
        lines.append(f"| {a.due or '—'} | {cell(a.task)} | {cell(a.assignee)} | {link(a.source, a.source, 'wiki')} |")
    return "\n".join(lines) + "\n"


def generate(root: Path) -> dict[str, str]:
    """생성할 파일의 {레포 기준 경로: 내용}을 돌려준다."""
    domains = wikilib.load_domains(root)
    decisions = load_decisions(root)
    questions = load_open_questions(root)

    outputs = {}
    counts = {}
    for domain in domains:
        decided = [d for d in decisions if d.status == "decided" and domain.name in d.domains]
        open_questions = [q for q in questions if domain.name in q.domains]
        outputs[f"{wikilib.DOMAIN_PAGES_DIR}/{domain.name}.md"] = domain_page(domain, decided, open_questions)
        counts[domain.name] = (len(decided), len(open_questions))
    outputs["wiki/index.md"] = index_page(domains, counts)
    outputs["wiki/log.md"] = log_page(decisions)
    outputs["wiki/action-items.md"] = action_items_page(load_action_items(root))
    return outputs


def write(root: Path, outputs: dict[str, str]) -> None:
    pages_dir = root / wikilib.DOMAIN_PAGES_DIR
    pages_dir.mkdir(parents=True, exist_ok=True)
    # 목록에서 빠진 도메인의 페이지를 지운다.
    for page in pages_dir.glob("*.md"):
        if f"{wikilib.DOMAIN_PAGES_DIR}/{page.name}" not in outputs:
            page.unlink()
    for rel, content in outputs.items():
        (root / rel).write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="위키 생성 파일 만들기")
    parser.add_argument("--root", type=Path, default=wikilib.REPO_ROOT)
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 만들 수 있는지만 확인한다")
    args = parser.parse_args()

    outputs = generate(args.root.resolve())
    if args.dry_run:
        print(f"생성 가능: 파일 {len(outputs)}개")
        return 0
    write(args.root.resolve(), outputs)
    print(f"생성 완료: 파일 {len(outputs)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
