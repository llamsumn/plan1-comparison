"""The ported method is auditable against the repository it came from.

`evidence/PROVENANCE.toml`'s `[[ported]]` rows do for executable code what its
`[[file]]` rows do for evidence: name the source, the commit, and a hash. The
discipline has to be the same, because the failure is the same — a copy that has
quietly become something other than what it claims to be.

It is asserted in both directions, for the reason `test_vendored_evidence.py`
gives at greater length: a row whose file changed must fail, and so must a file
that arrived with no row. The second is the one that lets code accumulate
unrecorded.

**And the thing this file exists to prevent.** Before #16, three separate places
resolved a sibling `../arap-deform-3dgs` working tree, and the suite silently
reported a different number depending on what else was checked out beside it. The
last test here is the guard against that coming back by any route.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from plan1.provenance import REPO_ROOT, load_evidence, sha256_file

RECORD = load_evidence()

#: What the port deliberately left behind. `descriptors.py` and `noise.py` are the
#: geometry reader, paused on a diagnosed shrinking-ball defect: on the penguin,
#: which is a surface shell, thickness is not a local property, so the estimator's
#: premise does not hold. That is the risk this repository exists to be safe from,
#: and its absence is asserted rather than assumed — a later port that swept it in
#: "for completeness" would be the single most expensive mistake available here.
NOT_PORTED = ("box_b/descriptors.py", "box_b/noise.py")

#: Every directory the port writes into. Anything executable outside `plan1/`,
#: `scripts/` and `tests/` came from the method repository and needs a row.
PORTED_TREES = ("arap_core", "box_b", "examples", "data", "tests/method")


def ported_files_on_disk() -> list[Path]:
    return sorted(
        path
        for tree in PORTED_TREES
        for path in (REPO_ROOT / tree).rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
    )


# ── the record describes what is there ──────────────────────────────────────
@pytest.mark.parametrize("entry", RECORD.ported, ids=lambda e: e.path)
def test_every_ported_file_hashes_to_its_recorded_value(entry):
    path = RECORD.resolve_ported(entry.path)
    assert path.is_file(), f"{entry.path} is recorded but absent"
    assert sha256_file(path) == entry.sha256


@pytest.mark.parametrize("entry", RECORD.ported, ids=lambda e: e.path)
def test_every_ported_row_names_its_repository_commit_and_reason(entry):
    assert entry.source_repo == "arap-deform-3dgs"
    assert re.fullmatch(r"[0-9a-f]{40}", entry.source_commit), entry.source_commit
    assert entry.why


# ── and what is there is described ──────────────────────────────────────────
def test_every_ported_file_has_a_provenance_row():
    """The direction that is easy to omit and does all the work."""
    recorded = {RECORD.resolve_ported(entry.path) for entry in RECORD.ported}
    unrecorded = [
        str(path.relative_to(REPO_ROOT))
        for path in ported_files_on_disk()
        if path not in recorded
    ]
    assert not unrecorded, f"ported with no provenance row: {unrecorded}"


def test_the_ported_record_is_not_empty_in_a_way_that_would_make_this_vacuous():
    """19 = 10 `arap_core` modules + 2 `box_b` + the example + the asset + 5 tests.

    Derived by listing the port, not by reading the count back off the record —
    which is the whole difference between an assertion and a restatement.
    """
    assert len(RECORD.ported) == len(ported_files_on_disk()) == 19


# ── what deliberately did not come ──────────────────────────────────────────
@pytest.mark.parametrize("path", NOT_PORTED)
def test_the_paused_geometry_reader_did_not_travel(path):
    assert not (REPO_ROOT / path).exists(), (
        f"{path} is the paused shrinking-ball track. It is the risk this "
        f"repository exists to be safe from; porting it needs a decision, not a "
        f"copy."
    )


def test_the_thirty_one_method_tests_are_all_of_the_method_tests():
    """47 of `arap-deform-3dgs`'s 78 tests belong to the paused track. 31 came."""
    assert len(list((REPO_ROOT / "tests" / "method").glob("test_*.py"))) == 5


# ── nothing resolves a sibling any more ─────────────────────────────────────
#: The two shapes every deleted resolution had. `parents[2]` climbs out of the
#: repository and guesses at what is beside it; the name is what it guessed at.
SIBLING = "arap-deform" "-3dgs"


def _live_strings_and_parent_climbs(tree: ast.AST) -> list[str]:
    """String literals and `…parents[2]` subscripts in *executing* code.

    Parsed rather than grepped, because prose is not code. `CONTEXT.md`,
    `PROVENANCE.toml` and the docstrings in this suite all have to name
    `arap-deform-3dgs` — that is the provenance of the copy and recording it is
    required. A line of text mentioning the sibling is a fact about where the code
    came from; an expression resolving it is the dependency #16 removed. Only the
    second is a finding, so only the second is looked for.
    """
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node not in docstrings
            and SIBLING in node.value
        ):
            found.append(f"line {node.lineno}: string {node.value!r}")
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == 2
        ):
            found.append(f"line {node.lineno}: .parents[2] — climbs out of the repo")
    return found


def test_no_file_in_the_repository_resolves_a_sibling_working_tree():
    """#16's acceptance criterion, as an executable check rather than a claim.

    Three places used to do this — `tests/conftest.py`'s `sys.path` injection,
    `test_conformance.py`'s own resolve, and `build_table.py`'s `METHOD_REPO`
    together with the git-HEAD read behind it. Deleting them is easy; keeping them
    deleted is what this test is for, because each one was added in good faith to
    solve a real problem and the same reasoning will recur.

    This file is exempt from itself. It is the only place that must name the
    forbidden shapes in order to look for them, and it ships no path resolution.
    """
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        for hit in _live_strings_and_parent_climbs(ast.parse(path.read_text())):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{hit}")
    assert not offenders, offenders


def test_the_published_table_still_names_nothing_outside_the_repository():
    """The footer used to print a value read off a sibling's `.git`."""
    from scripts.build_table import render_table

    text = render_table()
    assert "arap-deform-3dgs" not in text
    assert "../" not in text
    assert "3D/" not in text
