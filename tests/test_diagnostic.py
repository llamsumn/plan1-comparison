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


#: Below this, a residual is the floating-point floor rather than a measurement.
#: Two runs that both land under it agree about everything that can be known;
#: comparing them to each other is comparing rounding noise.
NOISE_FLOOR = 1e-9

#: Above the floor, agreement is required to this relative tolerance. The widest
#: real gap observed between two BLAS backends on the same numpy and scipy was
#: about 4e-15 relative (`3-delta`, 0.1599935921759021 against …15), so 1e-6
#: leaves six orders of headroom and would still catch a genuine regression.
RELATIVE_TOLERANCE = 1e-6


def test_the_ladder_has_the_same_shape_as_the_committed_record(executed, committed):
    """Structure is exactly reproducible, so it is compared exactly.

    The id, the phase, the name, the unit and the threshold are all written by
    the source rather than computed from it. A change in any of them means the
    ladder itself changed, which is never incidental.
    """
    mismatches = [
        (c["id"], {k: c[k] for k in ("phase", "id", "name", "unit", "threshold")},
         {k: f[k] for k in ("phase", "id", "name", "unit", "threshold")})
        for c, f in zip(committed, executed, strict=True)
        if any(c[k] != f[k] for k in ("phase", "id", "name", "unit", "threshold"))
    ]
    assert not mismatches, mismatches


def test_every_rung_reaches_the_same_verdict_as_the_committed_record(executed, committed):
    """`passed`, exactly. This is the record's actual content."""
    mismatches = [
        (c["id"], c["passed"], f["passed"])
        for c, f in zip(committed, executed, strict=True)
        if c["passed"] != f["passed"]
    ]
    assert not mismatches, mismatches


def test_every_measured_value_agrees_with_the_committed_one(executed, committed):
    """Values agree to within the floating-point floor — not bit-for-bit.

    **This started life as a bit-for-bit dict comparison and was wrong.** It
    passed on the machine that generated the record and failed on the first
    genuinely fresh clone: 20 of the 40 values differ in their last bits between
    BLAS backends, on identical numpy 2.5.1 and scipy 1.18.0. `L3` reads
    1.4218748958580352e-15 in one and 1.2560739669470201e-15 in the other. Every
    one of the 20 still passes its threshold, because every one is a residual
    whose *magnitude* is the finding and whose last bits are the platform's.

    Demanding bit-identity there would have made this suite pass in exactly one
    directory on exactly one machine — the failure mode this entire repository
    exists to close, reintroduced by the test written to close it. So:

    * below `NOISE_FLOOR`, two values agree about everything knowable, and only
      the verdict is compared (which the test above does);
    * above it, they must agree to `RELATIVE_TOLERANCE`, which is six orders
      wider than the widest observed platform gap and still tight enough that a
      real regression cannot hide in it.
    """
    mismatches = []
    for c, f in zip(committed, executed, strict=True):
        want, got = c["value"], f["value"]
        if not isinstance(want, (int, float)) or not isinstance(got, (int, float)):
            if want != got:  # "nan", "inf", None, or a string — compare exactly
                mismatches.append((c["id"], want, got))
            continue
        if abs(want) <= NOISE_FLOOR and abs(got) <= NOISE_FLOOR:
            continue
        scale = max(abs(want), abs(got))
        if abs(want - got) > RELATIVE_TOLERANCE * scale:
            mismatches.append((c["id"], want, got, abs(want - got) / scale))
    assert not mismatches, mismatches


def test_the_values_that_are_exact_by_construction_are_exact(executed, committed):
    """Counts are integers, and integers do not drift between BLAS backends.

    Without this, the tolerance above would quietly excuse a solver that took 78
    iterations where the record says 77 — a real change, well inside 1e-6 of it.
    """
    exact = {c["id"] for c in committed if isinstance(c["value"], float)
             and c["value"].is_integer() and abs(c["value"]) >= 1}
    assert exact, "no integral-valued rungs found — this guard would be vacuous"
    for c, f in zip(committed, executed, strict=True):
        if c["id"] in exact:
            assert c["value"] == f["value"], (c["id"], c["value"], f["value"])


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
