"""The solver's strongest evidence, as something that executes.

The solver arrived with nothing that drives it. No test touched `driver`,
`global_step` or `local_step` — its entire evidence was an inline assertion in
`run_penguin.py` plus a JSON file nobody ran. Now that this repository ships the
solver, it ships the solver's validation as something a reader can run rather
than something they can read.

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
from typing import Any

import pytest

from plan1.provenance import REPO_ROOT

DIAGNOSTIC_DIR = REPO_ROOT / "diagnostics"
COMMITTED = DIAGNOSTIC_DIR / "arap_core_diagnostic.json"

#: The three modules that have to be *reached* rather than assumed. The
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

#: Above the floor, agreement is required to this relative tolerance. It is
#: calibrated on *residuals* — the 29 of 40 rungs whose recorded value is at or
#: below 1e-8, 13 of them exactly zero, because the quantity is supposed to
#: vanish and the digits that remain are rounding. The widest gap observed among
#: those between two BLAS backends on the same numpy and scipy was about 4e-15
#: relative, so 1e-6 leaves six orders of headroom and would still catch a
#: genuine regression. The other 11 are not residuals, and this constant was
#: never measured against them — see `WIDER_TOLERANCE`.
RELATIVE_TOLERANCE = 1e-6


#: Rungs that are **not** residuals, with the tolerance each one's construction
#: supports and the reason it needs one. Every entry is here because it was
#: *observed* to move, never on speculation — `.github/workflows/verify.yml`
#: says so in as many words, and `B2` (2.74, also a converged-solve output) is
#: deliberately absent because it reproduced on Linux and has earned nothing.
#:
#: `3-delta` is `‖delta_soln − uniform_soln‖ / ‖uniform_soln − X‖`: a ratio of
#: differences between two *separately converged* solves of a non-convex energy,
#: each stopped when `max‖p_new − p‖ < 1e-11` — a bound on the last *step*,
#: which is not a bound on the distance to the limit point. ARAP's local step
#: takes an SVD per vertex, and where a configuration is near-degenerate the
#: branch LAPACK picks can send the alternation to a different — equally valid —
#: local minimum. Nothing about that is bounded by machine epsilon. Measured:
#: this Mac reads 0.1599935921759021 and the ubuntu-latest runner
#: 0.16272343632353745, 1.68e-2 apart, both clearing the 0.1 threshold and
#: reaching the same verdict. 5e-2 admits that with three times the headroom and
#: still cannot reach the threshold — which is not a matter of taste but the
#: property `test_no_widened_tolerance_can_admit_a_value_that_flips_the_verdict`
#: enforces, against a margin of 0.375.
WIDER_TOLERANCE: dict[str, tuple[float, str]] = {
    "3-delta": (
        5e-2,
        "ratio of differences between three separately converged solves of a "
        "non-convex energy; reproducibility is bounded by the alternation's "
        "choice of local minimum, not by machine epsilon",
    ),
}


def relative_tolerance_for(rung_id: str) -> float:
    """The tolerance this rung's *kind of quantity* actually supports.

    `RELATIVE_TOLERANCE` was measured on residuals and then applied to all forty
    rungs, which is this project's recurring mistake in its mildest form yet: a
    constant calibrated in one place and assumed to generalise. It does not
    generalise to a rung whose value is an O(1) output of a converged solve.
    """
    widened = WIDER_TOLERANCE.get(rung_id)
    return RELATIVE_TOLERANCE if widened is None else widened[0]


def disagreements(
    committed: list[dict[str, Any]], executed: list[dict[str, Any]]
) -> list[tuple[Any, ...]]:
    """Every rung whose re-run value does not agree with the recorded one.

    Pulled out of the test below so the *policy* can be exercised directly, on
    values chosen to sit either side of it. Driving it only through a live run
    of the ladder means it is tested at exactly one point per rung — the point
    this machine happens to produce — which is how the tolerance came to be
    calibrated on one class of rung and applied to all of them.
    """
    found: list[tuple[Any, ...]] = []
    for c, f in zip(committed, executed, strict=True):
        want, got = c["value"], f["value"]
        if not isinstance(want, (int, float)) or not isinstance(got, (int, float)):
            if want != got:  # "nan", "inf", None, or a string — compare exactly
                found.append((c["id"], want, got))
            continue
        if abs(want) <= NOISE_FLOOR and abs(got) <= NOISE_FLOOR:
            continue
        scale = max(abs(want), abs(got))
        tolerance = relative_tolerance_for(c["id"])
        if abs(want - got) > tolerance * scale:
            found.append((c["id"], want, got, abs(want - got) / scale))
    return found


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

    **And it was wrong a second time, one level up.** 2026-08-09, the first CI
    run this repository ever had: 863 passed and `3-delta` failed, 1.68e-2 apart
    between this Mac and ubuntu-latest. The rewrite above fixed the comparison
    and left the *calibration* unexamined — 1e-6 was measured on residuals and
    then spent on all forty rungs. `WIDER_TOLERANCE` is where that assumption
    now has to be stated per rung and argued for.
    """
    assert not (found := disagreements(committed, executed)), found


# ── the tolerance policy, exercised away from this machine's one data point ──
def _one_rung(rung_id, want, got, threshold=0.1):
    """A committed/executed pair carrying a single rung, for driving the policy."""
    base = {"phase": "3", "id": rung_id, "name": rung_id, "unit": "rel", "notes": ""}
    return (
        [{**base, "value": want, "threshold": threshold, "passed": True}],
        [{**base, "value": got, "threshold": threshold, "passed": True}],
    )


#: What ubuntu-latest measured for `3-delta` on 2026-08-09, against what this Mac
#: records. Transcribed from the failing run rather than re-derived, which is why
#: it is a literal here and not a computation. The run is identified by the line
#: it printed — `AssertionError: [('3-delta', 0.1599935921759021,
#: 0.16272343632353745, 0.01677597406563921)]`, workflow `verify`, job `gate`,
#: `1 failed, 863 passed in 14.48s` — and not by a URL: a link into the Actions
#: tab is exactly the kind of reference `tests/audit.py` refuses, and it would rot
#: long before the number does.
CI_OBSERVED = ("3-delta", 0.1599935921759021, 0.16272343632353745)


def test_the_policy_admits_the_value_ci_measured_on_another_platform():
    """The failure this change exists to fix, pinned as a value rather than a story.

    Watched failing first, with `WIDER_TOLERANCE` empty: `[('3-delta',
    0.1599935921759021, 0.16272343632353745, 0.01677597406563921)]`.
    """
    assert not disagreements(*_one_rung(*CI_OBSERVED))


def test_the_policy_still_rejects_a_collapse_in_the_weight_response():
    """Widening is only defensible if it still refuses the thing worth catching.

    `3-delta` says a delta-shaped weight moves the solution by more than 10% of
    the uniform one. A wiring break drives that toward zero, and 0.12 is a
    quarter of the recorded response gone while *still passing the rung's own
    threshold* — exactly the regression the rung cannot see on its own and the
    value comparison has to.
    """
    found = disagreements(*_one_rung("3-delta", 0.1599935921759021, 0.12))
    assert [f[0] for f in found] == ["3-delta"]


def test_widening_one_rung_does_not_widen_any_other():
    """The old constant still governs the 39 rungs nothing was measured about.

    A 1e-3 gap on a residual is seven orders past its floor and stays a failure;
    the same gap on `3-delta` is inside what the platform is entitled to move it.
    """
    assert relative_tolerance_for("L3") == RELATIVE_TOLERANCE
    assert disagreements(*_one_rung("L3", 1.0, 1.001, threshold=1e-9))
    assert not disagreements(*_one_rung("3-delta", 1.0, 1.001))


def test_no_widened_tolerance_can_admit_a_value_that_flips_the_verdict(committed):
    """The property that makes the number above a derivation rather than a taste.

    A value tolerance wide enough to reach a rung's own threshold would let this
    test pass while `test_every_rung_reaches_the_same_verdict…` fails — the
    suite contradicting itself about the same run. So each widened tolerance is
    required to keep its entire accepted band on one side of the boundary.

    For a tolerance `t` against a recorded `want`, the band the comparison
    accepts is exactly `[want*(1-t), want/(1-t)]`: below `want` the scale is
    `want`, above it the scale is `got`. `3-delta` at 5e-2 accepts
    [0.152, 0.168] against a threshold of 0.1.
    """
    by_id = {c["id"]: c for c in committed}
    for rung_id, (tolerance, _reason) in WIDER_TOLERANCE.items():
        assert 0 < tolerance < 1, (rung_id, tolerance)
        record = by_id[rung_id]
        want, threshold = record["value"], record["threshold"]
        assert isinstance(threshold, (int, float)), (rung_id, threshold)
        lo, hi = sorted((want * (1 - tolerance), want / (1 - tolerance)))
        assert not lo <= threshold <= hi, (rung_id, tolerance, lo, threshold, hi)


def test_every_widened_rung_is_real_and_says_why_it_is_widened(committed):
    """A bare number here would be indistinguishable from having given up.

    The same rule `tests/test_coverage_surface.py` applies to an exclusion
    marker: the reason travels with the thing it excuses.
    """
    ids = {c["id"] for c in committed}
    for rung_id, (_tolerance, reason) in WIDER_TOLERANCE.items():
        assert rung_id in ids, rung_id
        assert len(reason.split()) >= 10, (rung_id, reason)


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
    """It used to live outside this repository and import `arap_core` from beside it.

    Here `ROOT` is this repository, so the real-asset smoke check (`G6`) picks up
    the ported `data/penguin_original.ply` — 23,548 Gaussians — rather than
    skipping. That it ran at all is the evidence that the port and the diagnostic
    landed in the same place.
    """
    smoke = next(r for r in executed if r["id"] == "G6")
    assert smoke["passed"]
    assert "N=23548" in smoke["notes"], smoke["notes"]
