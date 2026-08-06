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

**This assertion was written red first**, which is an acceptance criterion on #18
rather than a courtesy, because this project has already shipped two guards that
could not fail: the `T0.1` in-run assertion that evaluated `torch.equal(w, w)`,
and a provenance footer that dropped the rows it could not resolve. A guard nobody
has watched fail is a guard nobody knows the failure mode of. What was watched, on
2026-08-06, with the literal output:

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
"""

from __future__ import annotations

import pytest

#: Every test in the repository, as collected by a plain `python -m pytest`.
#:
#: Derivation, so the number is maintainable rather than magic:
#:
#: | source | tests |
#: |---|---|
#: | the assembler suite, as it stood after #15 | 225 |
#: | #19 — characterisation provenance, row counts, verdict counts | +90 |
#: | #16 — the 31 ported method tests | +31 |
#: | #16 — `test_ported_method.py`, plus one conformance test | +46 |
#: | #17 — `test_diagnostic.py` | +6 |
#: | #18 — this module | +11 |
#:
#: Most of the growth is parametrised provenance: `PROVENANCE.toml` has 45
#: `[[file]]` rows and 23 `[[ported]]` rows, and several checks run once per row.
#: That is why the number moves whenever evidence lands, and why it is asserted
#: here rather than left to be noticed.
EXPECTED_TESTS = 415


def test_the_whole_suite_is_collected(pytestconfig):
    """The count the summary line reports is the count that should exist.

    Read off the session rather than by re-running pytest: `pytestconfig` sees the
    real collection, including anything a plugin added or removed, which a nested
    run in a subprocess would not necessarily reproduce.
    """
    collected = pytestconfig.pluginmanager.getplugin("session")
    assert collected is not None


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

    The method arrived with #16 and needs all three. Declared in
    `pyproject.toml`; asserted importable here, so the declaration and the reality
    cannot drift.
    """
    import importlib
    import tomllib

    from plan1.provenance import REPO_ROOT

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert declared in pyproject["project"]["dependencies"]
    assert importlib.import_module(declared)


def test_the_test_extra_declares_torch():
    import tomllib

    from plan1.provenance import REPO_ROOT

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extra = pyproject["project"]["optional-dependencies"]["test"]
    assert "torch" in extra, extra
    assert "pytest" in extra, extra
