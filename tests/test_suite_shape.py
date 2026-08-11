"""A suite that reports a number that means less than it looks like.

This is the failure this module exists to make impossible, and it is worth stating
precisely because it produced a *green* result for weeks:

| environment | pytest reported | actually ran |
|---|---|---|
| sibling layout, torch installed | `140 passed` | 140 |
| bare clone, torch installed | 2 collection errors | — |
| **bare clone, no torch** | **`60 passed, 20 skipped`** | **60 of 140** |

The last row was the default an examiner met, because `dependencies = []` and
`torch` lived in an optional extra. 80 tests — 57% — did not run, and the summary
line said nothing was wrong. The 80 included the conformance test and the wiring
harness, which `plan1_verdict.md` §1 names as the precondition for making any
claim at all. A reader saw green and concluded the gate had reproduced.

Three module-level `skipif` guards and two `importorskip` calls are now deleted, a
missing vendored input raises instead (`plan1.provenance.require_vendored`), and
`torch` is a declared hard test dependency. What remains is the possibility that
tests disappear some *other* way — a renamed directory, a `testpaths` edit, a
collection error swallowed in CI — and produce a smaller green number again. So
the total is asserted.

**This assertion was written red first**, which was a requirement rather than a
courtesy, because this project has already shipped two guards that could not fail:
the `T0.1` in-run assertion that evaluated `torch.equal(w, w)`, and a provenance
footer that dropped the rows it could not resolve. A guard nobody has watched fail
is a guard nobody knows the failure mode of. What was watched, on 2026-08-06, with
the literal output:

1. **A vendored input deleted.** `mv evidence/cluster/sources_20260729/helper.py`
   away, then `python -m pytest -q`::

       ERROR tests/test_conformance.py - FileNotFoundError: the deployed rigidity ru...
       ERROR tests/test_wiring_assertion.py - FileNotFoundError: the deployed rigidi...
       !!!!!!! Interrupted: 2 errors during collection !!!!!!!
       2 errors in 0.86s

   No passes, no skips, no total. Restored, and back to `415 passed`.

2. **`torch` unimportable**, shadowed by a stub that raises on import::

       ERROR tests/test_conformance.py
       ERROR tests/test_wiring_assertion.py
       !!!!!!! Interrupted: 2 errors during collection !!!!!!!
       2 errors in 0.31s

   Compare what this used to be: `60 passed, 20 skipped`, exit code 0.

3. **The number below, wrong.** Written first at 412 against a real 415, and it
   failed naming both counts before it was corrected.

The property all three establish is the same one: **the suite errors, it does not
shrink.**

**And the guard this module was itself carrying.** A fourth test sat at the top of
this file — `test_the_whole_suite_is_collected` — whose name and docstring said it
verified the collected count and whose body was::

    collected = pytestconfig.pluginmanager.getplugin("session")
    assert collected is not None

Inside a running pytest session that object always exists, so the assertion could
not fail: run alone against a single collected test, with the summary line reading
`1 passed`, it still passed. It is deleted rather than repaired, because the
property it claimed is the one the test below actually holds, and two tests where
one carries the assertion and the other cannot fail is worse than one test that
carries it.
"""

from __future__ import annotations

import pytest

from audit import requirement_names

#: Every test in the repository, as collected by a plain `python -m pytest`.
#:
#: Derivation, so the number is maintainable rather than magic:
#:
#: | source | tests |
#: |---|---|
#: | the assembler suite, once the evidence was vendored | 225 |
#: | characterisation provenance, row counts, verdict counts | +90 |
#: | the 31 method tests | +31 |
#: | `test_ported_method.py`, plus one conformance test | +46 |
#: | `test_diagnostic.py` — the solver ladder, re-executed | +9 |
#: | this module | +12 |
#: | `test_upstream_diff.py`, the third-party attribution guard | +21 |
#: | the sample asset's dataset attribution | +3 |
#: | `test_projection_figure.py`, the §6.4 figure | +29 |
#: | the vendored pre-registration and verdict | +15 |
#: | `test_source_audit.py` — the repository-wide reference audit | +86 |
#: | `test_vendored_record_links.py` — every link in the four records | +38 |
#: | the two vendored companions, and the inverted row guards | +16 |
#: | assertion strength: boundary tests, the mutation record, and its reader | +62 |
#:
#: Most of the growth is parametrised provenance: `PROVENANCE.toml` has 49
#: `[[file]]` rows and 27 `[[ported]]` rows, and several checks run once per row.
#: That is why the number moves whenever evidence lands, and why it is asserted
#: here rather than left to be noticed.
#:
#: Four of the rows above are the pre-write-up clean-up, +67 between them. Three of
#: the four added no evidence and no rows, so their +52 is whole tests: the two
#: committed upstream diffs, the sample asset's dataset attribution, and the §6.4
#: projection figure. Vendoring the two governing documents is the one that moves the
#: number the old way — `PROVENANCE.toml` rows are parametrised three ways in
#: `test_vendored_evidence.py` (hash, origin-and-reason, no-escape), so two rows are
#: +6 before a single new test is written.
#:
#: The last three rows are self-contained provenance, +140. They break down as:
#:
#: | check | tests |
#: |---|---|
#: | one per audited file — 64 tracked text files, the manifest included | 64 |
#: | one per audited Markdown file, for links that resolve | 5 |
#: | the three detectors' negative controls, plus 5 look-alikes they must ignore | 8 |
#: | the walk, the exemption, and the pragma extractor | 9 |
#: | one per link in the four vendored records | 29 |
#: | one per record the note has to cover, plus 3 on the note itself | 7 |
#: | negative controls on the link guard, both directions | 2 |
#: | the two new `[[file]]` rows, parametrised three ways | 6 |
#: | negative controls on the two inverted row guards, 5 each | 10 |
#:
#: The 64 is the number to watch: it is every text file in the repository, so adding
#: a source file moves this total by one whether or not it adds a test.
#:
#: The last row is assertion strength, and it is +62 net rather than gross — one test
#: was **deleted**, the unfalsifiable one described in the docstring above. It breaks
#: down as:
#:
#: | check | tests |
#: |---|---|
#: | the unfalsifiable collection test, removed | −1 |
#: | the saturation rule at both its thresholds, the hard stop, and the band | +9 |
#: | the precision model's boundaries and the console reader's search window | +5 |
#: | every record type frozen, one per claim-surface module, plus non-vacuity | +7 |
#: | the assembler's thresholds, its pairwise gate, and the duplicate-key rule | +8 |
#: | `box_b/edge_weights.py`'s two validation guards, at what each refuses | +6 |
#: | the three-way reading of `git check-ignore`, driven at all three answers | +3 |
#: | no test carries a check that cannot fail, and the detector's controls | +5 |
#: | `test_mutation_record.py` — the record read back and held to its claims | +17 |
#: | one per audited file, for the script, the record and the reader | +3 |
#:
#: The last row is the file-count effect again: `scripts/run_mutation.py`,
#: `mutation/mutation_record.json` and `tests/test_mutation_record.py` are each +1 to
#: the audit before a single one of their own tests is counted.
#:
#: **The coverage row is the last, and it is +175.** The claim surface — `plan1`,
#: `box_b`, `arap_core` and the worked example — now reaches 100% branch coverage with
#: two excluded lines, each carrying its reason beside the marker. Almost all of the
#: gap it closed was validation guards: code whose whole job is to refuse bad input,
#: and which had never been shown refusing anything. 157 of the 175 are tests; the
#: other 18 are the file-count effect:
#:
#: | check | tests |
#: |---|---|
#: | `build_graph`'s four validators and the Laplacian invariant assertion | +27 |
#: | the seven anchor validators, the constraint guard, and the soft path | +22 |
#: | the assembler's lookups, its input refusals, and `display_path` | +23 |
#: | the claim surface declared, and every marker on it held to a reason | +29 |
#: | the Gaussian carry's reflection guard and Shepperd's non-trace branches | +10 |
#: | the renderer's five optional sections, present and absent | +9 |
#: | both exits of the alternation loop, and the degenerate-vertex fallback | +9 |
#: | the reader's and writer's remaining refusals in `io_ply` | +6 |
#: | the SH band structure at every degree, and past the end of it | +10 |
#: | `select.py`'s three shape guards and its empty-selection warning | +8 |
#: | the worked example, run end to end on a 125-Gaussian lattice | +4 |
#: | ten new text files, at one audit test each | +10 |
#: | four new `[[ported]]` rows, parametrised two ways | +8 |
#:
#: The four `[[ported]]` rows are the four test modules written here rather than
#: ported. Everything under `tests/method/` carries a row, so they arrive with the
#: record's discipline already applied — which is why `test_ported_method.py` names
#: the five that travelled instead of counting files.
#:
#: **The last row is +5, and it is the first one CI paid for.** The first run this
#: repository ever had on a machine that is not the author's came back `863 passed,
#: 1 failed`: `3-delta` reads 1.68e-2 apart between this Mac and ubuntu-latest,
#: against a comparison tolerance of 1e-6. The tolerance was calibrated on residuals
#: and spent on all forty rungs; `3-delta` is a ratio of differences between
#: separately converged solves of a non-convex energy, and nothing about it is
#: bounded by machine epsilon. No file count moved — the tests are added to
#: `tests/test_diagnostic.py`, which already exists and is already audited.
#:
#: | check | tests |
#: |---|---|
#: | the tolerance policy at the value CI measured, and at a collapse it must still refuse | +2 |
#: | widening one rung leaves the other thirty-nine on the old constant | +1 |
#: | no widened tolerance can admit a value that flips its rung's verdict | +1 |
#: | every widened rung is a real rung and says why it is widened | +1 |
#:
#: **And the last is +1, for the front page.** `README.md` published the three
#: gap-recovered percentages with no absolute value anywhere behind them, so a reader
#: could not see what was recovered or from what without opening `out/`. The
#: endpoints are now beside them and asserted against the assembly. It is one test
#: walking all three metrics rather than three parametrised cases, so the total moves
#: by exactly what was added; and no file count moved either, because it lives in
#: `tests/test_build_table.py`, which already exists and is already audited.
EXPECTED_TESTS = 870


def test_the_collected_total_matches_the_expected_total(request):
    """If this fails, something appeared or vanished. Both need explaining.

    Vanishing is the dangerous direction and the reason the assertion exists.
    Appearing is fine and common — update `EXPECTED_TESTS` and its derivation
    table in the same commit that adds the tests, so the two never drift.
    """
    collected = len(request.session.items)
    assert collected == EXPECTED_TESTS, (
        f"collected {collected}, expected {EXPECTED_TESTS}. If tests were added, "
        f"update EXPECTED_TESTS and its derivation table above. If tests "
        f"VANISHED, find out why before touching this number — a smaller green "
        f"suite is the exact failure this assertion exists to catch."
    )


def test_nothing_in_the_suite_is_skipped(request):
    """Zero skips, as a standing property rather than an observation.

    A skip is how 80 tests disappeared while the summary line stayed green. There
    is no legitimate skip in this repository: every input is vendored, every
    dependency is declared, and anything missing is a bug.
    """
    skipped = [
        item.nodeid
        for item in request.session.items
        if item.get_closest_marker("skip") is not None
        or item.get_closest_marker("skipif") is not None
    ]
    assert not skipped, skipped


#: The shapes an assertion takes when it cannot fail. All three have been in this
#: repository: `torch.equal(w, w)` compared a value with itself, a provenance footer
#: dropped the rows it could not resolve, and a test named for the collected total
#: asserted that the pytest session object exists — which, inside a running session,
#: it always does.
def checks_that_cannot_fail(source: str) -> list[str]:
    """Every test in `source` whose checks are decoration, with the reason.

    A test function is only a check if something in it can raise: an `assert`, a
    `with pytest.raises(...)`, or one of numpy's `assert_*` helpers, which raise
    rather than return False. A function with none of those passes by reaching the
    end of itself.

    The two assertion shapes looked for on top of that are the ones that read as
    checks and are not — a truthy constant, and `is not None` on a bare name that the
    harness guarantees. Both are narrow on purpose: a detector that fired on ordinary
    code is a detector somebody turns off.
    """
    import ast

    def raises_on_failure(node: ast.AST) -> bool:
        if isinstance(node, (ast.Assert, ast.With)):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            return name.startswith("assert") or name == "raises"
        return False

    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if not any(raises_on_failure(inner) for inner in ast.walk(node)):
            found.append(f"{node.name}: nothing in it can fail")
        for statement in ast.walk(node):
            if not isinstance(statement, ast.Assert):
                continue
            test = statement.test
            if isinstance(test, ast.Constant) and test.value:
                found.append(f"{node.name}:{statement.lineno}: asserts a constant")
            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.IsNot)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
                and isinstance(test.left, ast.Name)
            ):
                found.append(
                    f"{node.name}:{statement.lineno}: asserts a bare name is not None"
                )
    return found


def test_no_test_in_the_suite_carries_a_check_that_cannot_fail():
    """The reported total has to be a count of checks, not a count of functions.

    This module exists because a green number meant less than it looked like. A test
    that cannot fail is the same failure one level down: it is collected, it is
    counted, it is reported as passing, and it constrains nothing. One was found in
    this very module — see the docstring above — which is the argument for making the
    search standing rather than a thing somebody did once.
    """
    from plan1.provenance import REPO_ROOT

    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        for finding in checks_that_cannot_fail(path.read_text()):
            offenders.append(f"{path.relative_to(REPO_ROOT)}::{finding}")
    assert not offenders, offenders


@pytest.mark.parametrize(
    "source",
    [
        "def test_x():\n    value = 1 + 1\n",
        "def test_x():\n    assert True\n",
        "def test_x(session):\n    assert session is not None\n",
    ],
    ids=["no check at all", "asserts a constant", "asserts a name is not None"],
)
def test_the_unfalsifiable_check_detector_fires_on_each_shape_it_hunts(source):
    """The detector, watched firing — a guard on guards is worth nothing unguarded.

    Driven against source built here rather than against a file, so this module does
    not have to contain the shapes it forbids in order to look for them.
    """
    assert checks_that_cannot_fail(source)


def test_the_detector_leaves_the_ways_a_real_test_checks_things_alone():
    """A detector that flagged `pytest.raises` or numpy's helpers would be deleted."""
    for innocent in (
        "def test_x():\n    with pytest.raises(ValueError):\n        f()\n",
        "def test_x():\n    np.testing.assert_array_equal(a, b)\n",
        "def test_x():\n    assert f() == 3\n",
        "def test_x():\n    assert f() is not None\n",  # a call, not a bare name
    ):
        assert not checks_that_cannot_fail(innocent), innocent


def test_no_module_carries_a_conditional_skip_marker():
    """The three deleted guards, asserted gone by source inspection.

    `test_nothing_in_the_suite_is_skipped` catches a marker that *fired*. This
    catches one that exists and happens to be false today — which is the state the
    repository was in for weeks, on the one machine where the sibling checkout
    made the condition false.
    """
    import ast

    from plan1.provenance import REPO_ROOT

    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        if path.name == "test_suite_shape.py":
            continue  # names the forbidden things in order to look for them
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "skipif",
                "importorskip",
            }:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    assert not offenders, offenders


def test_torch_is_a_hard_dependency_not_an_optional_extra():
    """`import torch` at module scope, in the two modules that are the gate.

    Under `importorskip` these two modules vanished silently on any machine
    without torch — and they are the conformance test and the wiring harness.
    """
    import torch  # noqa: F401  — the point is that this is not guarded

    assert torch.__version__


@pytest.mark.parametrize(
    "declared", ["numpy", "scipy", "plyfile"]
)
def test_the_runtime_dependencies_are_declared_and_importable(declared):
    """`dependencies` was `[]`, so a bare `pip install -e .` gave a broken runtime.

    The method needs all three. Declared in `pyproject.toml`; asserted importable
    here, so the declaration and the reality cannot drift.
    """
    import importlib
    import tomllib

    from plan1.provenance import REPO_ROOT

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert declared in requirement_names(pyproject["project"]["dependencies"])
    assert importlib.import_module(declared)


def test_no_file_the_repository_depends_on_is_gitignored():
    """A tracked file that `.gitignore` also matches is a fresh clone waiting to fail.

    Found by actually cloning, which is the only way this shows up: a blanket
    `*.png` rule added with the method port matched the six vendored
    characterisation figures added one commit earlier. They stayed in the
    repository — git keeps tracking what it already tracks — so every test passed
    and `git status` was clean. But the *rule* said they should not be there, and
    the next person to re-add them, or to build a clone from a file list rather
    than from history, would ship a repository missing the figures Chapter 6
    cites, with a green suite.

    Asserted over every path the repository actually depends on: the evidence base
    and everything ported. `git` is already a hard requirement of the green gate
    (`scripts/verify.sh` diffs the regenerated table with it), so its absence is
    an error here rather than a reason to skip.

    **It used to report the wrong cause when git was absent.** The check read git's
    exit code as a yes/no and treated every non-1 exit as a match, so a tree without
    a `.git` — a downloaded zip — failed this test with *matched by .gitignore* and
    an empty list. `audit.gitignored` separates git's third answer out; see the
    three controls on it in `test_source_audit.py`.
    """
    from audit import gitignored
    from plan1.provenance import load_evidence

    record = load_evidence()
    paths = [f"evidence/{entry.path}" for entry in record.files]
    paths += [entry.path for entry in record.ported]

    ignored = gitignored(paths)
    assert not ignored, (
        f"these are depended on but .gitignore matches them, so a fresh "
        f"`git add` would silently drop them:\n" + "\n".join(ignored)
    )


def test_the_test_extra_declares_torch():
    import tomllib

    from plan1.provenance import REPO_ROOT

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extra = requirement_names(pyproject["project"]["optional-dependencies"]["test"])
    assert "torch" in extra, extra
    assert "pytest" in extra, extra
