"""The solver's strongest evidence, as something that executes.

`arap-deform-3dgs`'s suite does not drive the solver. No test there touches
`driver`, `global_step` or `local_step` — the solver's entire evidence was an
inline assertion in `run_penguin.py` plus a JSON file in an archive nobody ran.
Now that this repository ships the solver (#16), it ships the solver's validation
as something a reader can run rather than something they can read.

**The ladder is re-executed, not re-read.** Comparing a committed JSON against
itself is the tautology this project has shipped twice — the retracted `T0.1`
assertion that evaluated `torch.equal(w, w)`, and the four-artefact provenance
footer that dropped rows it could not resolve. So `diagnostics/run_diagnostic.py`
is imported and its six phases are *run*, and the 40 records that come out are
compared field by field against `diagnostics/arap_core_diagnostic.json`.

That distinction paid for itself immediately. Run against the ported core, 39 of
the 40 entries reproduced bit-for-bit and one did not: `G5` asserted that SH bands
1 and above are left *untouched* — a boundary check written to pin the DC-only
stub, correct when it was written and obsolete since B1 replaced the stub with
real Wigner-D. A tautological check would have reported 40/40 green and hidden it.
`G5` is rewritten in the ported copy, with the original quoted at the call site;
both divergences are recorded in `evidence/PROVENANCE.toml`.

Runtime is about 2 seconds, so this belongs in the default suite rather than
behind a marker.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from types import ModuleType

import pytest

from plan1.provenance import REPO_ROOT

DIAGNOSTIC_DIR = REPO_ROOT / "diagnostics"
COMMITTED = DIAGNOSTIC_DIR / "arap_core_diagnostic.json"

#: The three modules the ticket requires be *reached* rather than assumed. The
#: diagnostic drives the solver end to end, so all three execute — but "the
#: driver runs" is the kind of claim that is easy to assert and easy to be wrong
#: about, so it is observed rather than believed (see the tracing test below).
SOLVER_MODULES = ("arap_core.driver", "arap_core.global_step", "arap_core.local_step")


def _load_diagnostic() -> ModuleType:
    """Import `run_diagnostic.py` without running `main()`.

    `main()` calls `write_artifacts()`, which would overwrite the committed record
    this test compares against — turning the comparison into precisely the
    self-referential check the module docstring says it must not be. The phases
    are therefore called directly.
    """
    spec = importlib.util.spec_from_file_location(
        "run_diagnostic", DIAGNOSTIC_DIR / "run_diagnostic.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def executed():
    """Run all six phases once, and hand back the records they produced."""
    module = _load_diagnostic()
    with contextlib.redirect_stdout(io.StringIO()):
        for phase in (
            module.phase1,
            module.phase2,
            module.phase3,
            module.phase4,
            module.phase5,
            module.phase6,
        ):
            phase()
    return module.RECORDS


@pytest.fixture(scope="module")
def committed():
    return json.loads(COMMITTED.read_text())


# ── the ladder runs, and its answer is the recorded one ─────────────────────
def test_the_ladder_produces_forty_records(executed, committed):
    assert len(executed) == 40
    assert len(committed) == 40


def test_every_executed_record_matches_the_committed_one(executed, committed):
    """Field by field, in order — the id, the value, the threshold and the pass.

    Compared as whole dicts rather than on `passed` alone: a check that still
    passes while its measured value has moved by an order of magnitude is a
    finding, and reducing the record to a boolean would discard it.
    """
    mismatches = [
        (c["id"], c, f) for c, f in zip(committed, executed, strict=True) if c != f
    ]
    assert not mismatches, mismatches


def test_all_forty_pass(executed):
    """The record is only evidence if the ladder is green when re-run."""
    failed = [(r["id"], r["name"], r["value"], r["notes"]) for r in executed if not r["passed"]]
    assert not failed, failed


def test_the_committed_record_is_not_what_is_being_asserted_against_itself(committed):
    """The guard on the guard.

    If someone later replaces the `executed` fixture with a second read of the
    committed file, every test above still passes and means nothing. This pins
    the property that makes them mean something: the comparison's left side comes
    from running code that imports `arap_core`.
    """
    module = _load_diagnostic()
    assert module.RECORDS == [], "a freshly imported module has run nothing yet"
    with contextlib.redirect_stdout(io.StringIO()):
        module.phase1()
    assert module.RECORDS, "phase1 produced no records — the ladder did not run"
    assert [r["id"] for r in module.RECORDS] == [c["id"] for c in committed[:7]]


# ── the three solver modules are reached, confirmed rather than assumed ─────
def test_the_driver_and_both_steps_are_actually_executed():
    """`driver`, `global_step` and `local_step` all run — observed by tracing.

    The ticket asks for this to be confirmed rather than assumed, and there is
    only one way to do that honestly: watch the interpreter enter the files. A
    module being *imported* proves nothing about whether any of its code ran,
    which is the same shape of mistake as reading a green summary line and
    concluding a skipped test passed.
    """
    module = _load_diagnostic()
    seen: set[str] = set()
    wanted = {name.rsplit(".", 1)[-1] + ".py" for name in SOLVER_MODULES}

    def tracer(frame, event, arg):
        if event == "call":
            filename = frame.f_code.co_filename
            name = filename.rsplit("/", 1)[-1]
            if name in wanted and "arap_core" in filename:
                seen.add(name)
        return None

    old = sys.getprofile()
    try:
        sys.setprofile(tracer)
        with contextlib.redirect_stdout(io.StringIO()):
            module.phase1()
    finally:
        sys.setprofile(old)

    assert seen == wanted, f"never entered: {sorted(wanted - seen)}"


# ── it runs with no sibling and no archive ──────────────────────────────────
def test_the_diagnostic_resolves_nothing_outside_this_repository(executed):
    """It used to live in `~/3D` and import `arap_core` from beside it.

    Here `ROOT` is this repository, so the real-asset smoke check (`G6`) picks up
    the ported `data/penguin_original.ply` — 23,548 Gaussians — rather than
    skipping. That it ran at all is the evidence that the port and the diagnostic
    landed in the same place.
    """
    smoke = next(r for r in executed if r["id"] == "G6")
    assert smoke["passed"]
    assert "N=23548" in smoke["notes"], smoke["notes"]
