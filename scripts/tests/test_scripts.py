"""scripts/의 형식 검사와 생성 스크립트 테스트.

    python -m unittest discover -s scripts/tests
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import check  # noqa: E402
import generate  # noqa: E402
import wikilib  # noqa: E402

REPO = SCRIPTS.parent
SOURCE = "raw/specs/2026-11-06-mvp-prd.md"

# 템플릿의 빈 값을 채울 샘플
SAMPLE = {
    "title": "방 이름 정책",
    "decided_at": "2026-11-06",
    "source": SOURCE,
    "durability": "permanent",
    "task": "방 이름 검증 추가",
    "assignee": "홍길동",
    "question": "방 변경 시 라벨인가 툴팁인가",
    "date": "2026-11-06",
    "author": "JaesungLeee",
    "domains": ["room"],
    "platforms": ["server", "android", "ios"],
    "attendees": ["홍길동"],
}


def frontmatter_lines(template: str) -> list[str]:
    text = (REPO / "templates" / template).read_text(encoding="utf-8")
    return text.split("---\n")[1].splitlines()


def template_keys(template: str) -> set[str]:
    """주석으로 처리하지 않은 키(필수 필드). items 아래 키는 `items.` 접두어를 붙인다."""
    keys = set()
    for line in frontmatter_lines(template):
        m = re.match(r"^(\s*)(?:- )?(\w+):", line)
        if m:
            keys.add(("items." if m.group(1) else "") + m.group(2))
    return keys - {"items"}


def template_enum(template: str, key: str) -> set[str]:
    """`status: open  # open(...) | done(...)` 같은 주석에서 값 목록을 뽑는다."""
    for line in frontmatter_lines(template):
        m = re.match(rf"^\s*{key}:[^#]*#\s*(.+)$", line)
        if m:
            return set(re.findall(r"([a-z_]+)\(", m.group(1)))
    raise AssertionError(f"{template}에 {key} 주석이 없다")


def fill(value, key=None):
    if isinstance(value, dict):
        return {k: fill(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [fill(v) for v in value] if value else SAMPLE[key]
    if value is None:
        return SAMPLE[key]
    return value


def filled_template(template: str) -> str:
    text = (REPO / "templates" / template).read_text(encoding="utf-8")
    _, fm, body = text.split("---\n", 2)
    data = fill(yaml.safe_load(fm))
    return "---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False) + "---\n" + body


class TempRepo:
    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        shutil.copy(REPO / "domains.yml", self.root / "domains.yml")
        self.write(SOURCE, "# MVP PRD\n")

    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def doc(self, rel: str, frontmatter: dict, body: str = "") -> Path:
        fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
        return self.write(rel, f"---\n{fm}---\n{body}")

    def errors(self, base: str | None = None) -> list[str]:
        checker = check.Checker(self.root)
        checker.check_docs()
        if base:
            checker.check_changes(base)
        return checker.errors

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
            cwd=self.root, check=True, capture_output=True,
        )

    def cleanup(self):
        self.dir.cleanup()


def decision(**overrides) -> dict:
    data = {
        "title": "방 이름 정책",
        "status": "decided",
        "decided_at": "2026-11-06",
        "domains": ["room"],
        "platforms": ["server", "android", "ios"],
        "source": SOURCE,
        "durability": "permanent",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not ...}


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def assertHasError(self, errors: list[str], fragment: str):
        self.assertTrue(any(fragment in e for e in errors), f"`{fragment}` 오류가 없다: {errors}")


class TemplateTest(RepoTestCase):
    """템플릿과 검사 코드가 어긋나지 않는지 본다."""

    def test_filled_templates_pass(self):
        self.repo.write("wiki/decisions/2026-11-06-방-이름-정책.md", filled_template("decision.md"))
        self.repo.write("wiki/action-items/specs/2026-11-06-mvp-prd.md", filled_template("action-items.md"))
        self.repo.write("wiki/open-questions/specs/2026-11-06-mvp-prd.md", filled_template("open-questions.md"))
        self.assertEqual(self.repo.errors(), [])
        generate.generate(self.repo.root)

    def test_required_fields_match(self):
        self.assertEqual(template_keys("decision.md"), set(check.DECISION_REQUIRED))
        self.assertEqual(
            template_keys("action-items.md"),
            {k for k in check.ACTION_REQUIRED if k != "items"} | {f"items.{k}" for k in check.ACTION_ITEM_REQUIRED},
        )
        self.assertEqual(
            template_keys("open-questions.md"),
            {k for k in check.OPEN_QUESTION_REQUIRED if k != "items"}
            | {f"items.{k}" for k in check.OPEN_QUESTION_ITEM_REQUIRED},
        )

    def test_status_values_match(self):
        self.assertEqual(template_enum("decision.md", "status"), set(check.DECISION_STATUS))
        self.assertEqual(template_enum("decision.md", "durability"), set(check.DURABILITY))
        self.assertEqual(template_enum("action-items.md", "status"), set(check.ACTION_STATUS))
        self.assertEqual(template_enum("open-questions.md", "status"), set(check.OPEN_QUESTION_STATUS))


class UnicodeTest(RepoTestCase):
    """macOS(NFD)에서 만든 한글 파일 이름과 NFC로 적은 경로를 같게 다룬다."""

    def test_nfd_file_with_nfc_source(self):
        nfc_source = "raw/meetings/2026-11-10-결제-정책.md"
        self.repo.write(unicodedata.normalize("NFD", nfc_source), "# 회의록\n")
        self.repo.doc("wiki/decisions/2026-11-10-환불.md", decision(source=nfc_source, decided_at="2026-11-10"))
        self.assertEqual(self.repo.errors(), [])

    def test_nfd_decision_file(self):
        name = unicodedata.normalize("NFD", "wiki/decisions/2026-11-06-방-이름-정책.md")
        self.repo.doc(name, decision())
        self.assertEqual(self.repo.errors(), [])
        page = generate.generate(self.repo.root)["wiki/domains/room.md"]
        self.assertIn("(../decisions/2026-11-06-방-이름-정책.md)", page)


class CheckTest(RepoTestCase):
    def test_decision_errors(self):
        self.repo.doc("wiki/decisions/a.md", decision(status="proposed"))
        self.repo.doc("wiki/decisions/b.md", decision(domains=[]))
        self.repo.doc("wiki/decisions/c.md", decision(domains=["payment"]))
        self.repo.doc("wiki/decisions/d.md", decision(source="raw/specs/없음.md"))
        self.repo.doc("wiki/decisions/e.md", decision(durability=..., decided_at="2026-13-01"))
        self.repo.doc("wiki/decisions/f.md", decision(supersedes=None))
        self.repo.doc("wiki/decisions/g.md", decision(platforms=["web"]))
        self.repo.write("wiki/decisions/h.md", "# frontmatter 없음\n")
        errors = self.repo.errors()
        self.assertHasError(errors, "a.md: `status` 값 `proposed`")
        self.assertHasError(errors, "b.md: `domains`가 1개 이상")
        self.assertHasError(errors, "c.md: 도메인 `payment`이 domains.yml에 없다")
        self.assertHasError(errors, "d.md: `source`가 가리키는 파일")
        self.assertHasError(errors, "e.md: 필수 필드 `durability`")
        self.assertHasError(errors, "e.md: `decided_at`은 YYYY-MM-DD")
        self.assertHasError(errors, "f.md: `supersedes` 값이 비어 있다")
        self.assertHasError(errors, "g.md: `platforms` 값 `web`")
        self.assertHasError(errors, "h.md: frontmatter가 없다")

    def test_decision_file_name_and_platforms(self):
        self.repo.doc("wiki/decisions/2026-11-07-날짜-다름.md", decision())
        self.repo.doc("wiki/decisions/날짜-없음.md", decision())
        self.repo.doc("wiki/decisions/2026-11-06-플랫폼-없음.md", decision(platforms=[]))
        errors = self.repo.errors()
        self.assertHasError(errors, "2026-11-07-날짜-다름.md: 파일 이름의 날짜 2026-11-07가 `decided_at` 2026-11-06와 다르다")
        self.assertHasError(errors, "날짜-없음.md: 파일 이름은 `YYYY-MM-DD-제목.md`")
        self.assertHasError(errors, "2026-11-06-플랫폼-없음.md: `platforms`가 1개 이상")

    def test_supersede_links(self):
        old = "wiki/decisions/2026-10-01-덱.md"
        new = "wiki/decisions/2026-11-06-덱.md"
        # 새 결정만 supersedes를 달고 옛 결정은 그대로 둔, 반만 처리한 대체
        self.repo.doc(old, decision(decided_at="2026-10-01"))
        self.repo.doc(new, decision(supersedes=old))
        self.repo.doc("wiki/decisions/2026-11-06-상태만.md", decision(status="superseded"))
        self.repo.doc("wiki/decisions/2026-11-06-포인터만.md", decision(superseded_by=new))
        errors = self.repo.errors()
        self.assertHasError(errors, f"{new}: 이 결정이 대체한 `{old}`의 `superseded_by`가 이 결정을 가리키지 않는다")
        self.assertHasError(errors, "상태만.md: `superseded`이면 `superseded_by`가 있어야 한다")
        self.assertHasError(errors, "포인터만.md: `superseded_by`가 있으면 `status`가 `superseded`여야 한다")
        self.assertHasError(errors, f"포인터만.md: 이 결정을 대체한 `{new}`의 `supersedes`가 이 결정을 가리키지 않는다")

    def test_supersede_links_complete(self):
        old = "wiki/decisions/2026-10-01-덱.md"
        new = "wiki/decisions/2026-11-06-덱.md"
        self.repo.doc(old, decision(decided_at="2026-10-01", status="superseded", superseded_by=new))
        self.repo.doc(new, decision(supersedes=old))
        self.assertEqual(self.repo.errors(), [])

    def test_path_mirrors_source(self):
        self.repo.doc("wiki/open-questions/meetings/다른-이름.md", {
            "source": SOURCE,
            "items": [{"question": "q", "domains": ["deck"], "status": "open", "resolved_by": SOURCE}],
        })
        self.repo.doc("wiki/action-items/specs/2026-11-06-mvp-prd.md", {
            "source": SOURCE, "items": [{"task": "t", "assignee": "가", "status": "open"}],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "다른-이름.md: 경로는 원본 경로를 따라 `wiki/open-questions/specs/2026-11-06-mvp-prd.md`여야 한다")
        self.assertHasError(errors, "items[1]: `resolved_by`는 `resolved`일 때만 쓴다")
        self.assertFalse(any("wiki/action-items/" in e for e in errors), errors)

    def test_domains_file(self):
        self.repo.write("domains.yml", "- name: room\n  scope: 방\n- name: Push_Notification\n  scope: 푸시\n- name: room\n  scope: 중복\n")
        errors = self.repo.errors()
        self.assertHasError(errors, "domains.yml: 도메인 이름 `Push_Notification`은 영어 소문자와 하이픈으로 쓴다")
        self.assertHasError(errors, "domains.yml: 도메인 `room`이 두 번 있다")

    def test_open_question_errors(self):
        self.repo.doc("wiki/open-questions/specs/x.md", {
            "source": SOURCE,
            "items": [
                {"question": "q1", "domains": ["deck"], "status": "resolved"},
                {"question": "q2", "domains": ["deck"], "status": "resolved",
                 "resolved_by": "wiki/decisions/없음.md"},
                {"question": "q3", "domains": [], "status": "open"},
            ],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "items[1]: `resolved`이면 `resolved_by`")
        self.assertHasError(errors, "items[2]: `resolved_by`가 가리키는 파일")
        self.assertHasError(errors, "items[3]: `domains`가 1개 이상")

    def test_action_item_errors(self):
        self.repo.doc("wiki/action-items/specs/x.md", {
            "source": SOURCE,
            "items": [
                {"task": "t", "status": "closed", "due": "내일"},
                {"task": "t", "assignee": "", "status": "open"},
            ],
        })
        errors = self.repo.errors()
        # 담당자는 선택 필드다. 없으면 통과하고, 줄만 있고 값이 비면 막는다
        self.assertFalse(any("`assignee`" in e for e in errors if "items[1]" in e))
        self.assertHasError(errors, "items[2]: `assignee` 값이 비어 있다")
        self.assertHasError(errors, "items[1]: `status` 값 `closed`")
        self.assertHasError(errors, "items[1]: `due`는 YYYY-MM-DD")

    def test_pr_changes(self):
        self.repo.write("raw/meetings/old.md", "원본\n")
        self.repo.write("raw/meetings/gone.md", "원본\n")
        self.repo.write("wiki/log.md", "생성\n")
        self.repo.write("wiki/domains/old.md", "생성\n")
        self.repo.git("init", "-q", "-b", "main")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "-m", "base")
        self.repo.git("checkout", "-q", "-b", "pr")
        self.repo.write("raw/meetings/old.md", "고침\n")
        (self.repo.root / "raw/meetings/gone.md").unlink()
        self.repo.write("raw/meetings/new.md", "새 원본\n")
        self.repo.write("wiki/index.md", "손으로 만듦\n")
        (self.repo.root / "wiki/log.md").unlink()
        self.repo.write("wiki/domains/room.md", "손으로 만듦\n")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "-m", "pr")
        errors = self.repo.errors(base="main")
        self.assertHasError(errors, "raw/meetings/old.md: raw/의 기존 파일을 고쳤다")
        self.assertHasError(errors, "raw/meetings/gone.md: raw/의 기존 파일을 지웠다")
        self.assertHasError(errors, "wiki/index.md: 생성 파일을 추가하거나 고쳤다")
        self.assertHasError(errors, "wiki/domains/room.md: 생성 파일을 추가하거나 고쳤다")
        self.assertFalse(any("raw/meetings/new.md" in e for e in errors))
        self.assertFalse(any("wiki/log.md" in e for e in errors))


class GenerateTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.repo.doc("wiki/decisions/2026-10-01-덱-장수.md", decision(
            title="덱 8장", decided_at="2026-10-01", domains=["deck"], status="superseded",
            superseded_by="wiki/decisions/2026-11-06-덱-장수.md"))
        self.repo.doc("wiki/decisions/2026-11-06-덱-장수.md", decision(
            title="덱 최대 10장", domains=["deck"], supersedes="wiki/decisions/2026-10-01-덱-장수.md"))
        self.repo.doc("wiki/decisions/2026-11-06-합류-알림.md", decision(
            title="합류 | 푸시", domains=["invitation", "notification"]))
        self.repo.doc("wiki/open-questions/specs/2026-11-06-mvp-prd.md", {"source": SOURCE, "items": [
            {"question": "라벨인가 툴팁인가", "domains": ["deck"], "status": "open"},
            {"question": "풀린 질문", "domains": ["deck"], "status": "resolved",
             "resolved_by": "wiki/decisions/2026-11-06-덱-장수.md"},
        ]})
        self.repo.doc("wiki/action-items/specs/2026-11-06-mvp-prd.md", {"source": SOURCE, "items": [
            {"task": "기한 없음", "status": "open"},
            {"task": "늦은 일", "assignee": "나", "status": "open", "due": "2026-12-01"},
            {"task": "이른 일", "assignee": "다", "status": "open", "due": "2026-11-20"},
            {"task": "끝난 일", "assignee": "라", "status": "done"},
        ]})
        self.assertEqual(self.repo.errors(), [])
        self.outputs = generate.generate(self.repo.root)

    def test_deterministic(self):
        self.assertEqual(self.outputs, generate.generate(self.repo.root))

    def test_domain_page(self):
        page = self.outputs["wiki/domains/deck.md"]
        self.assertIn("## 결정 (1)", page)
        self.assertIn("[덱 최대 10장](../decisions/2026-11-06-덱-장수.md)", page)
        self.assertNotIn("덱 8장", page)
        self.assertIn("## 미결 (1)", page)
        self.assertIn("- 라벨인가 툴팁인가 ([원본](../../raw/specs/2026-11-06-mvp-prd.md))", page)
        self.assertNotIn("풀린 질문", page)
        # 여러 도메인에 걸친 결정은 각 도메인 페이지에 나온다
        self.assertIn("합류 \\| 푸시", self.outputs["wiki/domains/invitation.md"])
        self.assertIn("합류 \\| 푸시", self.outputs["wiki/domains/notification.md"])
        self.assertIn("## 결정 (0)\n\n없음", self.outputs["wiki/domains/auth.md"])

    def test_index(self):
        index = self.outputs["wiki/index.md"]
        self.assertIn("| [deck](domains/deck.md) | 홈 카드 덱 구성, 정렬, 라벨 | 1 | 1 |", index)
        names = [d.name for d in wikilib.load_domains(self.repo.root)]
        self.assertEqual(re.findall(r"^\| \[([\w-]+)\]", index, re.M), names)

    def test_log(self):
        log = self.outputs["wiki/log.md"]
        rows = [line for line in log.splitlines() if line.startswith("| 2026")]
        self.assertTrue(rows[-1].startswith("| 2026-10-01"))
        self.assertIn("대체됨 → [덱 최대 10장](decisions/2026-11-06-덱-장수.md)", rows[-1])

    def test_action_items(self):
        page = self.outputs["wiki/action-items.md"]
        tasks = re.findall(r"^\| [^|]+ \| ([^|]+) \|", page, re.M)[2:]  # 머리글과 구분선 제외
        self.assertEqual([t.strip() for t in tasks], ["이른 일", "늦은 일", "기한 없음"])
        self.assertNotIn("끝난 일", page)
        self.assertIn("| — | 기한 없음 | — |", page)

    def test_write_removes_stale_domain_page(self):
        self.repo.write("wiki/domains/payment.md", "옛 도메인\n")
        generate.write(self.repo.root, self.outputs)
        self.assertFalse((self.repo.root / "wiki/domains/payment.md").exists())
        self.assertEqual((self.repo.root / "wiki/index.md").read_text(encoding="utf-8"), self.outputs["wiki/index.md"])


class RealRepoTest(unittest.TestCase):
    def test_repo_passes(self):
        checker = check.Checker(REPO)
        checker.check_docs()
        self.assertEqual(checker.errors, [])
        generate.generate(REPO)


if __name__ == "__main__":
    unittest.main()
