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
SOURCE = "raw/baseline/2026-11-06-mvp-prd.md"
# domains.yml에 없는 도메인. TempRepo가 실제 domains.yml을 복사하므로 실제 도메인이 될 수 있는 이름(예: payment)은 쓰지 않는다
UNKNOWN_DOMAIN = "not-a-domain"
# 테스트용 팀원 목록. 실제 people.yml이 바뀌어도 테스트가 흔들리지 않게 따로 둔다
PEOPLE = "- name: 홍길동\n  github: gildong\n  role: android\n- name: 김철수\n  role: design\n"

# 템플릿의 빈 값을 채울 샘플
SAMPLE = {
    "title": "방 이름 정책",
    "decided_at": "2026-11-06",
    "source": SOURCE,
    "durability": "permanent",
    "kind": "product",
    "task": "방 이름 검증 추가",
    "assignee": ["홍길동", wikilib.UNDECIDED_PERSON],
    "question": "방 변경 시 라벨인가 툴팁인가",
    "date": "2026-11-06",
    "author": "홍길동",
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
        shutil.copy(REPO / "platform-repository.yml", self.root / "platform-repository.yml")
        self.write("people.yml", PEOPLE)
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

    def commit_base(self) -> None:
        """지금 파일을 main에 커밋하고 PR 브랜치로 옮긴다."""
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "pr")

    def commit_pr(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "pr")

    def cleanup(self):
        self.dir.cleanup()


def decision(**overrides) -> dict:
    data = {
        "title": "방 이름 정책",
        "status": "decided",
        "kind": "product",
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
        self.repo.write("wiki/action-items/baseline/2026-11-06-mvp-prd.md", filled_template("action-items.md"))
        self.repo.write("wiki/open-questions/baseline/2026-11-06-mvp-prd.md", filled_template("open-questions.md"))
        self.assertEqual(self.repo.errors(), [])
        generate.generate(self.repo.root)

    def test_required_fields_match(self):
        self.assertEqual(template_keys("decision.md"), set(check.DECISION_REQUIRED))
        self.assertEqual(
            template_keys("action-items.md"),
            {k for k in check.ACTION_REQUIRED if k != "items"} | {f"items.{k}" for k in check.NEW_ACTION_ITEM_REQUIRED},
        )
        self.assertLess(set(check.ACTION_ITEM_REQUIRED), set(check.NEW_ACTION_ITEM_REQUIRED))
        self.assertEqual(
            template_keys("open-questions.md"),
            {k for k in check.OPEN_QUESTION_REQUIRED if k != "items"}
            | {f"items.{k}" for k in check.OPEN_QUESTION_ITEM_REQUIRED},
        )

    def test_status_values_match(self):
        self.assertEqual(template_enum("decision.md", "status"), set(check.DECISION_STATUS))
        self.assertEqual(template_enum("decision.md", "durability"), set(check.DURABILITY))
        self.assertEqual(template_enum("decision.md", "kind"), set(check.KINDS))
        self.assertEqual(template_enum("open-questions.md", "kind"), set(check.KINDS))
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
        self.repo.doc("wiki/decisions/c.md", decision(domains=[UNKNOWN_DOMAIN]))
        self.repo.doc("wiki/decisions/d.md", decision(source="raw/baseline/없음.md"))
        self.repo.doc("wiki/decisions/e.md", decision(durability=..., decided_at="2026-13-01"))
        self.repo.doc("wiki/decisions/f.md", decision(supersedes=None))
        self.repo.doc("wiki/decisions/g.md", decision(platforms=["web"]))
        self.repo.write("wiki/decisions/h.md", "# frontmatter 없음\n")
        self.repo.doc("wiki/decisions/i.md", decision(supersedes=["wiki/decisions/a.md", "wiki/decisions/a.md"]))
        self.repo.doc("wiki/decisions/j.md", decision(
            status="superseded", superseded_by=["wiki/decisions/a.md", "wiki/decisions/b.md"]))
        errors = self.repo.errors()
        self.assertHasError(errors, "a.md: `status` 값 `proposed`")
        self.assertHasError(errors, "b.md: `domains`가 1개 이상")
        self.assertHasError(errors, f"c.md: 도메인 `{UNKNOWN_DOMAIN}`이 domains.yml에 없다")
        self.assertHasError(errors, "d.md: `source`가 가리키는 파일")
        self.assertHasError(errors, "e.md: 필수 필드 `durability`")
        self.assertHasError(errors, "e.md: `decided_at`은 YYYY-MM-DD")
        self.assertHasError(errors, "f.md: `supersedes` 값이 비어 있다")
        self.assertHasError(errors, "g.md: `platforms` 값 `web`")
        self.assertHasError(errors, "h.md: frontmatter가 없다")
        self.assertHasError(errors, "i.md: `supersedes`에 `wiki/decisions/a.md`가 두 번 있다")
        self.assertHasError(errors, "j.md: `superseded_by`는 경로 하나여야 한다")

    def test_decision_file_name_and_platforms(self):
        self.repo.doc("wiki/decisions/2026-11-07-날짜-다름.md", decision())
        self.repo.doc("wiki/decisions/날짜-없음.md", decision())
        self.repo.doc("wiki/decisions/2026-11-06-플랫폼-없음.md", decision(platforms=[]))
        errors = self.repo.errors()
        self.assertHasError(errors, "2026-11-07-날짜-다름.md: 파일 이름의 날짜 2026-11-07가 `decided_at` 2026-11-06와 다르다")
        self.assertHasError(errors, "날짜-없음.md: 파일 이름은 `YYYY-MM-DD-제목.md`")
        self.assertHasError(errors, "2026-11-06-플랫폼-없음.md: `platforms`가 1개 이상")

    def test_decision_kind(self):
        self.repo.doc("wiki/decisions/2026-11-06-종류-없음.md", decision(kind=...))
        self.repo.doc("wiki/decisions/2026-11-06-종류-틀림.md", decision(kind="contract"))
        self.repo.doc("wiki/decisions/2026-11-06-한-플랫폼.md", decision(kind="tech", platforms=["android", "design"]))
        self.repo.doc("wiki/decisions/2026-11-06-공통-계약.md", decision(kind="tech", platforms=["server", "android"]))
        self.repo.doc("wiki/decisions/2026-11-06-한-플랫폼-기획.md", decision(platforms=["android"]))
        errors = self.repo.errors()
        self.assertHasError(errors, "2026-11-06-종류-없음.md: 필수 필드 `kind`")
        self.assertHasError(errors, "2026-11-06-종류-틀림.md: `kind` 값 `contract`")
        self.assertHasError(errors, "2026-11-06-한-플랫폼.md: `tech` 결정은 `platforms`에 android, ios, server 중 2개 이상")
        self.assertFalse(any("공통-계약.md" in e for e in errors), errors)
        self.assertFalse(any("한-플랫폼-기획.md" in e for e in errors), errors)

    def test_supersede_links(self):
        old = "wiki/decisions/2026-10-01-덱.md"
        new = "wiki/decisions/2026-11-06-덱.md"
        # 새 결정만 supersedes를 달고 옛 결정은 그대로 둔, 반만 처리한 대체
        self.repo.doc(old, decision(decided_at="2026-10-01"))
        self.repo.doc(new, decision(supersedes=old))
        self.repo.doc("wiki/decisions/2026-11-06-상태만.md", decision(status="superseded"))
        self.repo.doc("wiki/decisions/2026-11-06-포인터만.md", decision(superseded_by=new))
        # 여러 결정을 대체한 새 결정에서 목록의 이전 결정 하나만 superseded_by를 안 단 경우
        old_a = "wiki/decisions/2026-10-01-방-가.md"
        old_b = "wiki/decisions/2026-10-01-방-나.md"
        many = "wiki/decisions/2026-11-06-방.md"
        self.repo.doc(old_a, decision(decided_at="2026-10-01", status="superseded", superseded_by=many))
        self.repo.doc(old_b, decision(decided_at="2026-10-01"))
        self.repo.doc(many, decision(supersedes=[old_a, old_b]))
        # superseded_by로 새 결정을 가리키지만 새 결정의 supersedes 목록에 없는 결정
        stray = "wiki/decisions/2026-10-01-방-다.md"
        self.repo.doc(stray, decision(decided_at="2026-10-01", status="superseded", superseded_by=many))
        errors = self.repo.errors()
        self.assertHasError(errors, f"{new}: 이 결정이 대체한 `{old}`의 `superseded_by`가 이 결정을 가리키지 않는다")
        self.assertHasError(errors, "상태만.md: `superseded`이면 `superseded_by`가 있어야 한다")
        self.assertHasError(errors, "포인터만.md: `superseded_by`가 있으면 `status`가 `superseded`여야 한다")
        self.assertHasError(errors, f"포인터만.md: 이 결정을 대체한 `{new}`의 `supersedes`에 이 결정이 없다")
        self.assertHasError(errors, f"{many}: 이 결정이 대체한 `{old_b}`의 `superseded_by`가 이 결정을 가리키지 않는다")
        self.assertFalse(any(e.startswith(f"{many}: 이 결정이 대체한 `{old_a}`") for e in errors), errors)
        self.assertHasError(errors, f"{stray}: 이 결정을 대체한 `{many}`의 `supersedes`에 이 결정이 없다")

    def test_supersede_links_complete(self):
        old = "wiki/decisions/2026-10-01-덱.md"
        new = "wiki/decisions/2026-11-06-덱.md"
        self.repo.doc(old, decision(decided_at="2026-10-01", status="superseded", superseded_by=new))
        self.repo.doc(new, decision(supersedes=old))
        # 새 결정 하나가 이전 결정 둘을 목록으로 대체
        old_a = "wiki/decisions/2026-10-01-방-가.md"
        old_b = "wiki/decisions/2026-10-01-방-나.md"
        many = "wiki/decisions/2026-11-06-방.md"
        self.repo.doc(old_a, decision(decided_at="2026-10-01", status="superseded", superseded_by=many))
        self.repo.doc(old_b, decision(decided_at="2026-10-01", status="superseded", superseded_by=many))
        self.repo.doc(many, decision(supersedes=[old_a, old_b]))
        self.assertEqual(self.repo.errors(), [])

    def test_supersede_split_rejected(self):
        # 결정 하나를 두 결정으로 나눠 대체(1:N)하면 superseded_by가 하나만 가리켜 다른 쪽 짝이 맞지 않는다
        old = "wiki/decisions/2026-10-01-덱.md"
        new_a = "wiki/decisions/2026-11-06-덱-가.md"
        new_b = "wiki/decisions/2026-11-06-덱-나.md"
        self.repo.doc(old, decision(decided_at="2026-10-01", status="superseded", superseded_by=new_a))
        self.repo.doc(new_a, decision(supersedes=old))
        self.repo.doc(new_b, decision(supersedes=old))
        errors = self.repo.errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertHasError(errors, f"{new_b}: 이 결정이 대체한 `{old}`의 `superseded_by`가 이 결정을 가리키지 않는다")

    def test_supersede_cycle(self):
        a = "wiki/decisions/2026-11-06-가.md"
        b = "wiki/decisions/2026-11-06-나.md"
        c = "wiki/decisions/2026-11-06-다.md"
        # 짝은 모두 맞지만 가 → 나 → 다 → 가로 돌아 decided 결정이 없다
        self.repo.doc(a, decision(status="superseded", supersedes=c, superseded_by=b))
        self.repo.doc(b, decision(status="superseded", supersedes=a, superseded_by=c))
        self.repo.doc(c, decision(status="superseded", supersedes=b, superseded_by=a))
        self.repo.doc("wiki/decisions/2026-11-06-자기.md", decision(
            status="superseded",
            supersedes="wiki/decisions/2026-11-06-자기.md",
            superseded_by="wiki/decisions/2026-11-06-자기.md",
        ))
        errors = self.repo.errors()
        self.assertEqual(len(errors), 2, errors)
        self.assertHasError(errors, f"{a}: 대체 관계가 순환한다: {a} → {b} → {c} → {a}")
        self.assertHasError(errors, "자기.md: 대체 관계가 순환한다")

    def test_links_point_to_decisions(self):
        self.repo.doc("wiki/decisions/2026-11-06-원본-대체.md", decision(status="superseded", superseded_by=SOURCE))
        self.repo.doc("wiki/open-questions/baseline/2026-11-06-mvp-prd.md", {
            "source": SOURCE,
            "items": [{"question": "q", "domains": ["deck"], "kind": "product", "status": "resolved", "resolved_by": SOURCE}],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "원본-대체.md: `superseded_by`는 `wiki/decisions/` 아래 결정 문서")
        self.assertHasError(errors, "items[1]: `resolved_by`는 `wiki/decisions/` 아래 결정 문서")

    def test_path_mirrors_source(self):
        self.repo.doc("wiki/open-questions/meetings/다른-이름.md", {
            "source": SOURCE,
            "items": [{"question": "q", "domains": ["deck"], "kind": "product", "status": "open", "resolved_by": SOURCE}],
        })
        self.repo.doc("wiki/action-items/baseline/2026-11-06-mvp-prd.md", {
            "source": SOURCE, "items": [{"task": "t", "assignee": ["홍길동"], "status": "open"}],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "다른-이름.md: 경로는 원본 경로를 따라 `wiki/open-questions/baseline/2026-11-06-mvp-prd.md`여야 한다")
        self.assertHasError(errors, "items[1]: `resolved_by`는 `resolved`일 때만 쓴다")
        self.assertFalse(any("wiki/action-items/" in e for e in errors), errors)

    def test_domains_file(self):
        self.repo.write("domains.yml", "- name: room\n  scope: 방\n- name: Push_Notification\n  scope: 푸시\n- name: room\n  scope: 중복\n")
        errors = self.repo.errors()
        self.assertHasError(errors, "domains.yml: 도메인 이름 `Push_Notification`은 영어 소문자와 하이픈으로 쓴다")
        self.assertHasError(errors, "domains.yml: 도메인 `room`이 두 번 있다")

    def test_repositories_file(self):
        self.repo.write("platform-repository.yml", (
            "- platform: server\n  url: https://github.com/org/Server\n"
            "- platform: server\n  url: https://github.com/org/server-2\n"
            "- platform: design\n  url: https://github.com/org/design\n"
            "- platform: android\n  url: git@github.com:org/android.git\n"
            "- platform: ios\n  url: https://github.com/other/server\n"
        ))
        errors = self.repo.errors()
        self.assertHasError(errors, "platform-repository.yml: 플랫폼 `server`이 두 번 있다")
        self.assertHasError(errors, "platform-repository.yml: `platform` 값 `design`은")
        self.assertHasError(errors, "platform-repository.yml: `url` `git@github.com:org/android.git`은")
        self.assertHasError(errors, "platform-repository.yml: 레포 이름 `server`이 두 번 있다")

    def test_repository_name(self):
        repo = wikilib.Repository("server", "https://github.com/mash-up-kr/Team-MINO-Node")
        self.assertEqual(repo.name, "Team-MINO-Node")

    def test_tech_platforms_follow_repositories(self):
        # 레포가 없는 플랫폼은 `tech` 결정의 2개에 세지 않는다
        self.repo.write("platform-repository.yml", (
            "- platform: server\n  url: https://github.com/org/server\n"
            "- platform: android\n  url: https://github.com/org/android\n"
        ))
        self.repo.doc("wiki/decisions/2026-11-06-앱-공통.md", decision(kind="tech", platforms=["android", "ios"]))
        self.repo.doc("wiki/decisions/2026-11-06-서버-앱.md", decision(kind="tech", platforms=["server", "android"]))
        errors = self.repo.errors()
        self.assertHasError(errors, "2026-11-06-앱-공통.md: `tech` 결정은 `platforms`에 android, server 중 2개 이상")
        self.assertFalse(any("서버-앱.md" in e for e in errors), errors)

    def test_people_file(self):
        self.repo.write("people.yml", (
            "- name: 홍길동\n  github: gildong\n  role: android\n"
            "- name: 홍길동\n  role: design\n"
            "- name: 김철수\n  github: GilDong\n  role: backend\n"
        ))
        errors = self.repo.errors()
        self.assertHasError(errors, "people.yml: 이름 `홍길동`이 두 번 있다")
        self.assertHasError(errors, "people.yml: GitHub 아이디 `GilDong`가 두 번 있다")
        self.assertHasError(errors, "people.yml: `role` 값 `backend`")

    def test_people_file_reserved_name(self):
        self.repo.write("people.yml", PEOPLE + "- name: 알 수 없음\n  role: ios\n- name: 미정\n  role: ios\n")
        errors = self.repo.errors()
        self.assertHasError(errors, "people.yml: `알 수 없음`은 이름으로 쓸 수 없다")
        self.assertHasError(errors, "people.yml: `미정`은 이름으로 쓸 수 없다")

    def test_people_file_missing_name(self):
        self.repo.write("people.yml", "- name: 홍길동\n  role: android\n- role: design\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check.py"), "--root", str(self.repo.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "error: people.yml: 2번째 항목에 name과 role이 필요하다\n")

    def test_open_question_errors(self):
        self.repo.doc("wiki/open-questions/baseline/x.md", {
            "source": SOURCE,
            "items": [
                {"question": "q1", "domains": ["deck"], "kind": "product", "status": "resolved"},
                {"question": "q2", "domains": ["deck"], "kind": "product", "status": "resolved",
                 "resolved_by": "wiki/decisions/없음.md"},
                {"question": "q3", "domains": [], "kind": "product", "status": "open"},
                {"question": "q4", "domains": ["deck"], "status": "open"},
                {"question": "q5", "domains": ["deck"], "kind": "contract", "status": "open"},
            ],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "items[1]: `resolved`이면 `resolved_by`")
        self.assertHasError(errors, "items[2]: `resolved_by`가 가리키는 파일")
        self.assertHasError(errors, "items[3]: `domains`가 1개 이상")
        self.assertHasError(errors, "items[4]: 필수 필드 `kind`")
        self.assertHasError(errors, "items[5]: `kind` 값 `contract`")

    def test_action_item_errors(self):
        self.repo.doc("wiki/action-items/baseline/x.md", {
            "source": SOURCE,
            "items": [
                {"task": "t", "status": "closed", "due": "내일"},
                {"task": "t", "assignee": "", "status": "open"},
                {"task": "t", "assignee": [], "status": "open"},
            ],
        })
        errors = self.repo.errors()
        self.assertHasError(errors, "items[1]: `status` 값 `closed`")
        self.assertHasError(errors, "items[1]: `due`는 YYYY-MM-DD")
        # 레포 전체 검사는 담당자를 보지 않는다. 담당자는 PR에서 추가하거나 고친 파일만 본다
        self.assertFalse(any("`assignee`" in e for e in errors), errors)

    def test_old_action_items_not_checked(self):
        # 담당자 목록 규칙 전에 들어간 파일. PR에서 바뀌지 않았으면 담당자를 검사하지 않는다
        old = "wiki/action-items/baseline/2026-11-06-mvp-prd.md"
        self.repo.doc(old, {"source": SOURCE, "items": [
            {"task": "t", "assignee": "디자인 팀", "status": "open"},
            {"task": "t", "status": "open"},
            {"task": "t", "assignee": "윤지", "status": "done"},
        ]})
        self.repo.commit_base()
        self.repo.write("raw/meetings/2026-11-10-회의.md", "# 회의\n")
        self.repo.commit_pr()
        self.assertEqual(self.repo.errors(base="main"), [])

    def test_new_action_item_assignee_errors(self):
        old = "wiki/action-items/baseline/2026-11-06-mvp-prd.md"
        self.repo.doc(old, {"source": SOURCE, "items": [{"task": "t", "assignee": "디자인 팀", "status": "open"}]})
        self.repo.commit_base()
        new_source = "raw/meetings/2026-11-10-회의.md"
        self.repo.write(new_source, "# 회의\n")
        new = "wiki/action-items/meetings/2026-11-10-회의.md"
        self.repo.doc(new, {"source": new_source, "items": [
            {"task": "t", "status": "open"},
            {"task": "t", "assignee": [], "status": "open"},
            {"task": "t", "assignee": "홍길동", "status": "open"},
            {"task": "t", "assignee": ["길동", "디자인 팀", "gildong"], "status": "open"},
            {"task": "t", "assignee": ["홍길동", "홍길동"], "status": "open"},
        ]})
        # 기존 파일을 고치면(완료 표시 등) 새 규칙으로 검사한다
        self.repo.doc(old, {"source": SOURCE, "items": [{"task": "t", "assignee": "디자인 팀", "status": "done"}]})
        self.repo.commit_pr()
        errors = self.repo.errors(base="main")
        self.assertHasError(errors, f"{new} items[1]: 필수 필드 `assignee`가 없다")
        # 빈 목록은 "줄을 뺀다" 없이 이 오류 한 건만 낸다
        self.assertEqual([e for e in errors if e.startswith(f"{new} items[2]:")],
                         [f"{new} items[2]: `assignee`는 1명 이상인 목록이어야 한다. 정해지지 않았으면 `[{wikilib.UNDECIDED_PERSON}]`으로 쓴다"])
        self.assertHasError(errors, f"{new} items[3]: `assignee`는 1명 이상인 목록이어야 한다")
        # 이름 부분, 팀 이름, GitHub 아이디는 name이 아니다
        for value in ("길동", "디자인 팀", "gildong"):
            self.assertHasError(errors, f"{new} items[4]: `assignee` 값 `{value}`이 people.yml에 없다")
        self.assertHasError(errors, f"{new} items[5]: `assignee`에 `홍길동`이 두 번 있다")
        self.assertHasError(errors, f"{old} items[1]: `assignee`는 1명 이상인 목록이어야 한다")
        # 레포 전체 검사는 같은 파일을 오류로 보지 않는다
        self.assertEqual(self.repo.errors(), [])

    def test_new_action_item_assignee_values(self):
        self.repo.commit_base()
        self.repo.doc("wiki/action-items/baseline/2026-11-06-mvp-prd.md", {
            "source": SOURCE,
            "items": [
                {"task": "t", "assignee": ["홍길동", "김철수"], "status": "open"},
                {"task": "t", "assignee": ["홍길동", wikilib.UNKNOWN_PERSON], "status": "open"},
                {"task": "t", "assignee": ["홍길동", wikilib.UNDECIDED_PERSON], "status": "open"},
                {"task": "t", "assignee": [wikilib.UNDECIDED_PERSON], "status": "open"},
            ],
        })
        self.repo.commit_pr()
        self.assertEqual(self.repo.errors(base="main"), [])

    def test_pr_changes(self):
        self.repo.write("raw/meetings/old.md", "원본\n")
        self.repo.write("raw/meetings/gone.md", "원본\n")
        self.repo.write("raw/specs/.gitkeep", "")
        self.repo.write("raw/notes/2026-11-01-예전-채팅.md", "---\ndate: 2026-11-01\n---\n예전 원본\n")
        self.repo.write("wiki/log.md", "생성\n")
        self.repo.write("wiki/domains/old.md", "생성\n")
        self.repo.commit_base()
        self.repo.write("raw/meetings/old.md", "고침\n")
        (self.repo.root / "raw/meetings/gone.md").unlink()
        (self.repo.root / "raw/specs/.gitkeep").unlink()
        self.repo.write("raw/meetings/new.md", "새 원본\n")
        self.repo.write("raw/notes/2026-11-06-작성자-있음.md", filled_template("note.md"))
        self.repo.write("raw/notes/2026-11-06-작성자-빔.md", "---\ndate: 2026-11-06\nauthor:\n---\n메시지\n")
        self.repo.write("raw/notes/2026-11-06-작성자-없음.md", "---\ndate: 2026-11-06\n---\n메시지\n")
        self.repo.write("raw/notes/2026-11-06-작성자-알-수-없음.md", "---\ndate: 2026-11-06\nauthor: 알 수 없음\n---\n메시지\n")
        self.repo.write("raw/notes/2026-11-06-작성자-목록-밖.md", "---\ndate: 2026-11-06\nauthor: 최다은\n---\n메시지\n")
        self.repo.write("raw/notes/2026-11-06-작성자-여럿.md", "---\ndate: 2026-11-06\nauthor: [홍길동, 김철수]\n---\n메시지\n")
        self.repo.write("wiki/index.md", "손으로 만듦\n")
        (self.repo.root / "wiki/log.md").unlink()
        self.repo.write("wiki/domains/room.md", "손으로 만듦\n")
        self.repo.commit_pr()
        errors = self.repo.errors(base="main")
        self.assertHasError(errors, "raw/meetings/old.md: raw/의 기존 파일을 고쳤다")
        self.assertHasError(errors, "raw/meetings/gone.md: raw/의 기존 파일을 지웠다")
        self.assertHasError(errors, "wiki/index.md: 생성 파일을 추가하거나 고쳤다")
        self.assertHasError(errors, "wiki/domains/room.md: 생성 파일을 추가하거나 고쳤다")
        self.assertHasError(errors, "raw/notes/2026-11-06-작성자-빔.md: `author`가 없거나 비어 있다")
        self.assertHasError(errors, "raw/notes/2026-11-06-작성자-없음.md: `author`가 없거나 비어 있다")
        self.assertHasError(errors, "raw/notes/2026-11-06-작성자-목록-밖.md: `author` 값 `최다은`가 people.yml에 없다")
        self.assertHasError(errors, "raw/notes/2026-11-06-작성자-여럿.md: `author` 값")
        self.assertFalse(any(n in e for e in errors for n in ("작성자-있음", "작성자-알-수-없음", "예전-채팅")), errors)
        self.assertFalse(any("raw/meetings/new.md" in e for e in errors))
        self.assertFalse(any(".gitkeep" in e for e in errors), errors)
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
        self.repo.doc("wiki/decisions/2026-11-06-초대-실패-응답.md", decision(
            title="초대 실패 응답 형식", kind="tech", domains=["invitation"], platforms=["server", "android", "ios"]))
        self.repo.doc("wiki/open-questions/baseline/2026-11-06-mvp-prd.md", {"source": SOURCE, "items": [
            {"question": "라벨인가 툴팁인가", "domains": ["deck"], "kind": "product", "status": "open"},
            {"question": "정렬 기준을 서버가 주나", "domains": ["deck"], "kind": "tech", "status": "open"},
            {"question": "풀린 질문", "domains": ["deck"], "kind": "product", "status": "resolved",
             "resolved_by": "wiki/decisions/2026-11-06-덱-장수.md"},
        ]})
        self.repo.doc("wiki/action-items/baseline/2026-11-06-mvp-prd.md", {"source": SOURCE, "items": [
            {"task": "기한 없음", "assignee": [wikilib.UNDECIDED_PERSON], "status": "open"},
            {"task": "늦은 일", "assignee": ["홍길동", "김철수"], "status": "open", "due": "2026-12-01"},
            {"task": "이른 일", "assignee": ["김철수"], "status": "open", "due": "2026-11-20"},
            {"task": "끝난 일", "assignee": ["홍길동"], "status": "done"},
            # 담당자 목록 규칙 전에 들어간 문자열 담당자
            {"task": "예전 일", "assignee": "디자인 팀", "status": "open", "due": "2026-11-25"},
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
        self.assertIn("| [덱 최대 10장](../decisions/2026-11-06-덱-장수.md) | 기획 | 2026-11-06 |", page)
        self.assertIn("## 미결 (2)", page)
        self.assertIn("- [기획] 라벨인가 툴팁인가 ([원본](../../raw/baseline/2026-11-06-mvp-prd.md))", page)
        self.assertIn("- [기술] 정렬 기준을 서버가 주나", page)
        self.assertIn("| [초대 실패 응답 형식](../decisions/2026-11-06-초대-실패-응답.md) | 기술 |", self.outputs["wiki/domains/invitation.md"])
        self.assertNotIn("풀린 질문", page)
        # 여러 도메인에 걸친 결정은 각 도메인 페이지에 나온다
        self.assertIn("합류 \\| 푸시", self.outputs["wiki/domains/invitation.md"])
        self.assertIn("합류 \\| 푸시", self.outputs["wiki/domains/notification.md"])
        self.assertIn("## 결정 (0)\n\n없음", self.outputs["wiki/domains/auth.md"])

    def test_index(self):
        index = self.outputs["wiki/index.md"]
        self.assertIn("| [deck](domains/deck.md) | 홈 카드 덱 구성, 정렬, 라벨 | 1 | 2 |", index)
        names = [d.name for d in wikilib.load_domains(self.repo.root)]
        self.assertEqual(re.findall(r"^\| \[([\w-]+)\]", index, re.M), names)

    def test_log(self):
        log = self.outputs["wiki/log.md"]
        rows = [line for line in log.splitlines() if line.startswith("| 2026")]
        self.assertTrue(rows[-1].startswith("| 2026-10-01"))
        self.assertIn("대체됨 → [덱 최대 10장](decisions/2026-11-06-덱-장수.md)", rows[-1])
        self.assertIn("| [초대 실패 응답 형식](decisions/2026-11-06-초대-실패-응답.md) | 기술 | invitation | 유효 |", log)

    def test_log_many_superseded(self):
        new = "wiki/decisions/2026-11-06-방-정책.md"
        olds = ["wiki/decisions/2026-10-02-방-이름.md", "wiki/decisions/2026-10-02-방-색상.md"]
        for old, title in zip(olds, ["방 이름", "방 색상"]):
            self.repo.doc(old, decision(title=title, decided_at="2026-10-02", status="superseded", superseded_by=new))
        self.repo.doc(new, decision(title="방 정책 통합", supersedes=olds))
        self.assertEqual(self.repo.errors(), [])
        log = generate.generate(self.repo.root)["wiki/log.md"]
        rows = [line for line in log.splitlines() if line.startswith("| 2026-10-02")]
        self.assertEqual(len(rows), 2, log)
        for row in rows:
            self.assertIn("대체됨 → [방 정책 통합](decisions/2026-11-06-방-정책.md)", row)

    def test_action_items(self):
        page = self.outputs["wiki/action-items.md"]
        tasks = re.findall(r"^\| [^|]+ \| ([^|]+) \|", page, re.M)[2:]  # 머리글과 구분선 제외
        self.assertEqual([t.strip() for t in tasks], ["이른 일", "예전 일", "늦은 일", "기한 없음"])
        self.assertNotIn("끝난 일", page)
        self.assertIn("| — | 기한 없음 | 미정 |", page)
        self.assertIn("| 2026-12-01 | 늦은 일 | 홍길동, 김철수 |", page)
        self.assertIn("| 2026-11-25 | 예전 일 | 디자인 팀 |", page)

    def test_write_removes_stale_domain_page(self):
        self.repo.write(f"wiki/domains/{UNKNOWN_DOMAIN}.md", "옛 도메인\n")
        generate.write(self.repo.root, self.outputs)
        self.assertFalse((self.repo.root / f"wiki/domains/{UNKNOWN_DOMAIN}.md").exists())
        self.assertEqual((self.repo.root / "wiki/index.md").read_text(encoding="utf-8"), self.outputs["wiki/index.md"])


class RealRepoTest(unittest.TestCase):
    def test_repo_passes(self):
        checker = check.Checker(REPO)
        checker.check_docs()
        self.assertEqual(checker.errors, [])
        generate.generate(REPO)


if __name__ == "__main__":
    unittest.main()
