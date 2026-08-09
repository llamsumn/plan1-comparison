"""The method's own files cannot quietly become something else.

`evidence/PROVENANCE.toml`'s `[[ported]]` rows do for executable code what its
`[[file]]` rows do for evidence: say what each file is, and hash it. The discipline
has to be the same, because the failure is the same — a file that has stopped being
what the repository claims it is.

It is asserted in both directions, for the reason `test_vendored_evidence.py`
gives at greater length: a row whose file changed must fail, and so must a file
that arrived with no row. The second is the one that lets code accumulate
unrecorded.

The rows used to name two of this author's unpublished repositories and a commit in
each, and this module *required* it. They no longer do, and the assertion is
inverted rather than deleted — see
`test_no_ported_row_attributes_this_code_to_a_repository_nobody_can_read`.

**And the thing this file exists to prevent.** Three separate places once resolved a
sibling working tree, and the suite silently reported a different number depending
on what else was checked out beside it. The last test here is the guard against that
coming back by any route.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from audit import PRIVATE_REPOS, forbidden_references, origin_problems
from plan1.provenance import REPO_ROOT, PortedFile, load_evidence, sha256_file

RECORD = load_evidence()

#: What the port deliberately left behind. `descriptors.py` and `noise.py` are the
#: geometry reader, paused on a diagnosed shrinking-ball defect: on the penguin,
#: which is a surface shell, thickness is not a local property, so the estimator's
#: premise does not hold. That is the risk this repository exists to be safe from,
#: and its absence is asserted rather than assumed — a later port that swept it in
#: "for completeness" would be the single most expensive mistake available here.
NOT_PORTED = ("box_b/descriptors.py", "box_b/noise.py")

#: Every tree the method occupies. Anything executable outside `plan1/`, `scripts/`
#: and `tests/` is the method rather than the assembler, and needs a row: the six
#: below, each file identified in `PROVENANCE.toml` by what it is and what it hashes
#: to.
PORTED_TREES = (
    "arap_core",
    "box_b",
    "examples",
    "data",
    "tests/method",
    "diagnostics",
)


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
def test_no_ported_row_attributes_this_code_to_a_repository_nobody_can_read(entry):
    """The code is this project's own, and this repository is its published home.

    **This assertion used to require the opposite.** It read
    `assert entry.source_repo in {…}` against two literal repository names, and
    `assert re.fullmatch(r"[0-9a-f]{40}", entry.source_commit)` — it *mandated* that
    every row name one of two of this author's unpublished repositories and a commit
    inside it. 23 rows obliged, and the published table's footer printed one of those
    commits. None of it could be followed by a reader, and there was nobody to
    attribute to in any case.

    So the requirement is inverted rather than deleted: the property becomes "names
    nothing a reader cannot resolve" instead of disappearing. It was watched failing
    first, on 2026-08-08, 23 times with
    `AttributeError: 'PortedFile' object has no attribute 'source_repo'`.

    The property itself lives in `audit.origin_problems`, shared with the `[[file]]`
    row guard. Two assertions used to hold half of it each — this one forbade a
    repository and a commit, the other forbade a path — and a path is no more
    resolvable on a ported row than on a vendored one.

    What the rows were *for* is untouched, because it was never the commit.
    `test_the_vendored_reference_rule_is_the_one_that_was_ported` in the conformance
    suite checks `box_b/edge_weights.py` against the sha256 on its row and against
    the value the published footer prints, so all three fail together on an edit.
    Genuine third-party attribution is a different question and stays in full: see
    `upstream_repo` on the two cluster sources, and `attribution` below.
    """
    assert entry.why, f"{entry.path} has no reason for being here"
    problems = origin_problems(entry.origin)
    assert not problems, (
        f"{entry.path}'s origin is {entry.origin!r}:\n  " + "\n  ".join(problems)
    )
    assert re.fullmatch(r"[0-9a-f]{64}", entry.sha256), entry.sha256


@pytest.mark.parametrize(
    "bad_origin",
    [
        "",
        "copied from " + PRIVATE_REPOS[1],
        "ported at ede5fd3a1dda0b69ddb38648c0c97a77021021b0",
        "ported at ede5fd3",
        "ported under " + "#" + "16",
    ],
    ids=["empty", "private repository", "full commit", "short commit", "ticket"],
)
def test_the_origin_guard_fails_on_a_ported_row_that_cites_the_unreachable(bad_origin):
    """The guard above, driven against a deliberately bad row.

    The inverted assertion has to be able to fail, and the failures that matter are
    the ones the old assertion *required*: a repository name and a commit. Both are
    put to it here, in full and abbreviated form, because `ede5fd3` in prose is the
    same unresolvable citation as the 40-hex version and a guard that caught only
    the long one would be worked around by habit.

    The real guard is called rather than reimplemented, for the reason
    `test_vendored_evidence.py` gives at greater length.
    """
    bad = PortedFile(
        path="box_b/edge_weights.py",
        origin=bad_origin,
        sha256="0" * 64,
        why="a reason that is present, so the origin is what fails",
    )
    with pytest.raises(AssertionError):
        test_no_ported_row_attributes_this_code_to_a_repository_nobody_can_read(bad)


# ── the one row that is data, and owed to someone else ──────────────────────
#: Every other ported row is code this project wrote, copied between this project's
#: own repositories. `data/penguin_original.ply` is not: it is a 3DGS export of a
#: checkpoint trained on a third-party capture, so `source_repo` answers *where the
#: copy came from* while leaving *whom it is owed to* unrecorded. Those are different
#: questions and the port record only ever answered the first.
ATTRIBUTED = "data/penguin_original.ply"


def test_the_sample_asset_names_the_dataset_it_derives_from():
    """MIT permits redistributing it. Attribution is the condition, not a courtesy.

    Asserted on content rather than on the field merely existing, because "there is
    an attribution string" is satisfied by an empty gesture: the dataset has to be
    named, its licence has to be named, and the fact that this project did not train
    the checkpoint has to be there too — that last one is the claim a reader would
    otherwise reasonably infer in this repository's favour.
    """
    entry = RECORD.ported_file(ATTRIBUTED)
    assert entry.attribution, f"{ATTRIBUTED} has no dataset attribution"
    for owed in ("DiVa360", "MIT", "brown-ivl", "not trained here"):
        assert owed in entry.attribution, owed


def test_third_party_md_carries_the_same_attribution_where_a_reader_lands():
    """A field in a TOML file nobody opens is not attribution.

    `THIRD_PARTY.md` is where the licence question is answered for the whole
    repository, so the asset has to appear there as well — and both places are
    asserted so neither can be updated alone.
    """
    text = (REPO_ROOT / "THIRD_PARTY.md").read_text()
    assert "DiVa360" in text
    assert ATTRIBUTED in text
    assert "MIT" in text


def test_no_other_ported_row_claims_a_third_party_dataset():
    """One asset is owed to someone else. The rest are this project's own work, and
    saying so keeps the field meaningful rather than boilerplate on every row."""
    attributed = {e.path for e in RECORD.ported if e.attribution is not None}
    assert attributed == {ATTRIBUTED}


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
    """27 = 23 for the method + 4 for the solver diagnostic.

    The 23: 10 `arap_core` modules, 2 `box_b`, the example, the asset, 9 tests.
    The 4: `run_diagnostic.py`, `refs.py`, `arap_core_diagnostic.json`, and
    `cantilever_profile.csv` — which the ladder writes rather than anything copying.

    The tests were 5 and are 9. Four modules were authored here rather than
    ported, covering the solver core's guards: `build_graph`'s validators, the
    anchor validators and the soft-constraint path, both exits of the alternation
    loop, and the Gaussian carry's reflection guard. They carry rows because the
    tree carries rows, not because anything was copied — which is why
    `test_no_method_test_module_arrived_without_a_decision` names the five that
    travelled rather than counting files.

    Derived by listing the port, not by reading the count back off the record —
    which is the whole difference between an assertion and a restatement.
    """
    assert len(RECORD.ported) == len(ported_files_on_disk()) == 27


# ── what deliberately did not come ──────────────────────────────────────────
@pytest.mark.parametrize("path", NOT_PORTED)
def test_the_paused_geometry_reader_did_not_travel(path):
    assert not (REPO_ROOT / path).exists(), (
        f"{path} is the paused shrinking-ball track. It is the risk this "
        f"repository exists to be safe from; porting it needs a decision, not a "
        f"copy."
    )


#: The five test modules that travelled from the method repository. 47 of that
#: repository's 78 tests belong to the paused track and did not come; these five
#: files carried the 31 that did.
PORTED_METHOD_TESTS = frozenset(
    {
        "test_edge_weights.py",
        "test_edges.py",
        "test_gaussian_sh.py",
        "test_io_ply.py",
        "test_select.py",
    }
)


def test_no_method_test_module_arrived_without_a_decision():
    """A sixth *ported* module appearing is what this guards.

    **It used to assert a file count of five, and that was the wrong shape.** The
    property is about the port — something copied in from the paused track
    without anyone deciding to — and a count cannot tell a port from a test
    written here. It failed the moment this repository wrote its own tests for
    `arap_core`'s solver, which is not the event it exists to catch, and the only
    ways to satisfy it were to raise the number every time (making it a
    restatement) or to put new tests somewhere they do not belong.

    So the five are named. Anything else under `tests/method/` is authored here,
    is covered by the same `[[ported]]` row discipline as every other file in the
    tree, and is fine; one of the five *vanishing* is not, and that direction is
    asserted too.
    """
    present = {path.name for path in (REPO_ROOT / "tests" / "method").glob("test_*.py")}

    assert PORTED_METHOD_TESTS <= present, PORTED_METHOD_TESTS - present
    assert not {
        name for name in present - PORTED_METHOD_TESTS if "descriptor" in name or "noise" in name
    }, "a test for the paused geometry reader arrived without a decision"


# ── nothing resolves a sibling any more ─────────────────────────────────────
#: The two shapes every deleted resolution had. `parents[2]` climbs out of the
#: repository and guesses at what is beside it; the name is what it guessed at.
SIBLING = "arap-deform" "-3dgs"


def _live_strings_and_parent_climbs(tree: ast.AST) -> list[str]:
    """String literals and `…parents[2]` subscripts in *executing* code.

    Parsed rather than grepped, because prose is not code. `PROVENANCE.toml` names
    the source repository per row — that is the provenance of the copy and recording
    it is required. A line of text naming the sibling is a fact about where the code
    came from; an expression resolving it is the dependency the port removed. Only
    the second is a finding, so only the second is looked for.

    The prose in this repository no longer names it, and that is deliberate rather
    than a gap. Provenance is recorded in one authoritative place; repeating it
    across docstrings said nothing `PROVENANCE.toml` does not say better, and much
    of what it said was about how this work is positioned relative to other work
    rather than about where a byte came from. `SIBLING` below is the exception and
    has to be: it is the needle this guard hunts, and deleting it would leave a
    check that passes because it stopped looking.
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
    """No module reaches out of the repository, as an executable check.

    Three places used to do this — `tests/conftest.py`'s `sys.path` injection,
    `test_conformance.py`'s own resolve, and `build_table.py`'s `METHOD_REPO`
    together with the git-HEAD read behind it. Deleting them is easy; keeping them
    deleted is what this test is for, because each one was added in good faith to
    solve a real problem and the same reasoning will recur.

    **What this catches that the repository-wide audit does not.** `tests/audit.py`
    reads text and cannot tell prose from an expression; this parses, and looks for
    a `.parents[2]` subscript, which is a *climb out of the repository* rather than
    a string. The two overlap on the sibling's name and only this one sees the
    climb, so both are kept.

    This file is exempt from itself. It is the only place that must name the
    forbidden shapes in order to look for them, and it ships no path resolution.
    """
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        # Skip anything under a dot-directory. A virtualenv at `.venv/` is the
        # normal way to run the green gate, and `site-packages` is full of
        # third-party `parents[2]` climbs — torchgen and sympy both have one.
        # Scanning them says nothing about this repository and made the check
        # fail on the first genuinely fresh clone.
        if any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts):
            continue
        if "__pycache__" in path.parts:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        for hit in _live_strings_and_parent_climbs(ast.parse(path.read_text())):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{hit}")
    assert not offenders, offenders


def test_the_published_table_still_names_nothing_outside_the_repository():
    """The footer used to print a value read off a sibling's `.git`, and then a
    commit read out of the record. Both named a repository nobody can clone."""
    from scripts.build_table import render_table

    text = render_table()
    assert SIBLING not in text
    assert not forbidden_references(text)
    assert "../" not in text
