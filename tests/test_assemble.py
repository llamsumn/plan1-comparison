"""Tests for the assembler — the one seam.

External behaviour only: given these records and this manifest, this table or this
failure comes out. Negative cases carry as much weight as positive ones, because a
gate nothing can fail is not evidence.

**Which was true of the gate itself, in one respect, until it was measured.** The
comparability gate is this repository's first enforced claim, and its pairwise loops
could be made to skip pairs with the whole suite still green — because the one test
driving each perturbed a row that disagrees with an endpoint as well. Every boundary
and gate assertion added since was watched failing against the wrong implementation
before it was kept:

| the source, made wrong | the test that failed |
|---|---|
| `ordered[index + 1 :]`, primitive counts → `index + 2` | `test_the_gate_compares_a_disagreeing_pair_in_the_middle_of_the_manifest` |
| `ordered[index + 1 :]`, start fingerprints → `index - 1` | `test_the_gate_compares_a_pair_that_is_neither_adjacent_nor_an_endpoint_pair` |
| `if (b - n) != 0.0` → `if (b + n) != 0.0` | `test_rounding_intervals_that_touch_do_not_divide_by_zero` |
| `if len(family) < 2` → `< 3` | `test_two_null_family_runs_are_the_fewest_that_give_a_band` |
| `if not sweep: return None` → `if sweep:` | `test_a_manifest_with_no_imposed_rows_yields_no_saturation_verdict` |
| `if denominator == 0.0` → `!= 0.0` | `test_a_baseline_that_scores_identically_to_the_null_has_no_gap_to_express` |
| `if not rows` → `if rows` | `test_a_manifest_declaring_no_rows_at_all_raises` |
| `keys.count(k) > 1` → `> 2` (in `manifest.py`) | `test_two_rows_declaring_the_same_key_raise` |
"""

import math

import pytest

from conftest import (
    PARENT_CELLS,
    START,
    make_manifest,
    make_record,
    make_row,
    overlaps,
)
from plan1.assemble import (
    AssemblyError,
    ComparabilityError,
    ManifestError,
    assemble,
)
from plan1.records import METRICS


# ── the positive case, in both precision worlds ─────────────────────────────
def test_well_formed_rows_assemble_under_the_console_baseline(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)

    assert table.eval_step == 501
    assert table.num_primitives == 23548
    assert [r.key for r in table.rows] == ["null", "imposed16", "baseline"]

    # the shared start is printed in the table, so a reader can verify at a glance
    assert table.start["psnr"].value == pytest.approx(16.76434326171875)

    # point estimates in the console-baseline world. Each is the midpoint of an
    # interval, not a fact about the fifth decimal — which is what the guard below
    # exists to keep visible.
    imposed = table.row("imposed16")
    assert imposed.fractions["psnr"].value == pytest.approx(0.6362423, abs=1e-7)
    assert imposed.fractions["ssim"].value == pytest.approx(0.7249567, abs=1e-7)
    assert imposed.fractions["lpips"].value == pytest.approx(0.7924386, abs=1e-7)


def test_the_full_precision_world_produces_the_published_cells(
    three_row_case_full_precision,
):
    """The path every published number now travels: 63.6% / 72.6% / 80.4%."""
    manifest, records = three_row_case_full_precision
    imposed = assemble(manifest, records).row("imposed16")

    assert [round(imposed.fractions[m].value * 100, 1) for m in METRICS] == [
        63.6,
        72.6,
        80.4,
    ]
    for fraction in imposed.fractions.values():
        assert fraction.exact  # nothing coarse is left to widen them


# ── the guard: interval to interval, never point to interval ────────────────
@pytest.mark.parametrize("metric", METRICS)
def test_published_cells_are_compared_interval_to_interval(three_row_case, metric):
    """A cell printed at coarser precision is an interval, not an exact number.

    This replaces a retired test that asserted the parent spec's SSIM cell was
    wrong and Plan 1's value right. It was not: under the console baseline the
    assembler's own interval *contained* the parent's cell, so no correction was
    ever licensed. The rule is stated once, over all three metrics, rather than as
    a note about the one cell where the mistake happened to surface.
    """
    manifest, records = three_row_case
    fraction = assemble(manifest, records).row("imposed16").fractions[metric]
    cell = PARENT_CELLS[metric]
    assert overlaps(fraction, cell), (
        f"{metric}: assembler [{fraction.low:.6%}, {fraction.high:.6%}] does not "
        f"overlap the parent's {cell.value:.1%} -> "
        f"[{cell.interval[0]:.6%}, {cell.interval[1]:.6%}]"
    )


def test_the_full_precision_lpips_cell_legitimately_leaves_the_parent_interval(
    three_row_case_full_precision,
):
    """Why the guard above is NOT parametrised over the full-precision fixture.

    Once the baseline is bound to its own recovered record, every fraction is exact
    and its interval is zero-width — so overlap collapses back into the comparison
    being retracted. And here it genuinely fails: 80.4% is outside the parent's
    [79.15%, 79.25%]. That is not a correction of the parent and not a swapped run.
    The *input* sharpened. PSNR and SSIM did not move enough to leave their cells;
    LPIPS did, and the verdict explains it beside the claim it qualifies.
    """
    manifest, records = three_row_case_full_precision
    fractions = assemble(manifest, records).row("imposed16").fractions

    assert overlaps(fractions["psnr"], PARENT_CELLS["psnr"])
    assert overlaps(fractions["ssim"], PARENT_CELLS["ssim"])
    assert not overlaps(fractions["lpips"], PARENT_CELLS["lpips"])


def test_a_point_in_interval_guard_would_report_a_false_correction(three_row_case):
    """Why interval-to-interval, and not the obvious weaker form.

    Comparing the parent's cell as a *point* against the assembler's interval is
    the reasoning being retracted. Run over all three metrics it does not merely
    read as less rigorous — it manufactures a fresh correction of the parent, on
    PSNR this time, by exactly the same route.
    """
    manifest, records = three_row_case
    fractions = assemble(manifest, records).row("imposed16").fractions

    def point_in_interval(metric):
        f, cell = fractions[metric], PARENT_CELLS[metric]
        return f.low <= cell.value <= f.high

    assert not point_in_interval("psnr")  # the false correction it would report
    assert point_in_interval("ssim")
    assert point_in_interval("lpips")

    # and the form actually used passes on all three, PSNR included
    assert all(overlaps(fractions[m], PARENT_CELLS[m]) for m in METRICS)


def test_endpoints_carry_no_fractions(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)
    assert table.row("null").fractions is None
    assert table.row("baseline").fractions is None


def test_assembly_is_deterministic(three_row_case):
    manifest, records = three_row_case
    assert assemble(manifest, records) == assemble(manifest, records)


# ── the comparability gate: three ways to fail it ───────────────────────────
def test_disagreeing_start_fingerprint_raises(three_row_case):
    manifest, records = three_row_case
    records["imposed16"] = make_record(
        "imposed16",
        22.953351974487305,
        0.9442539215087891,
        0.06339161843061447,
        start={**START, "psnr": 16.9},  # a different starting checkpoint
    )
    with pytest.raises(ComparabilityError, match="start"):
        assemble(manifest, records)


def test_disagreeing_eval_step_raises(three_row_case):
    manifest, records = three_row_case
    records["baseline"] = make_record("baseline", 25.055, 0.9535, 0.056, eval_step=1000)
    with pytest.raises(ComparabilityError, match="evaluation step"):
        assemble(manifest, records)


def test_disagreeing_primitive_count_raises(three_row_case):
    manifest, records = three_row_case
    records["null"] = make_record(
        "null",
        19.277395248413086,
        0.9198831915855408,
        0.09161172062158585,
        num_primitives=23549,
    )
    with pytest.raises(ComparabilityError, match="primitive count"):
        assemble(manifest, records)


def test_the_gate_does_not_weaken_when_a_coarse_row_comes_first():
    """Rows are compared pairwise, not each against the first row.

    Comparing at the coarser of two precisions is not transitive: two
    full-precision rows differing in the fourth decimal would both agree with a
    three-decimal console line. Anchoring the gate on whichever row happens to be
    listed first would let that pair through.
    """
    rows = [
        make_row("coarse_first", "baseline"),
        make_row("fine_a", "null"),
        make_row("fine_b", "imposed", rigidity=16),
    ]
    records = {
        # listed first, and coarse enough to agree with both of the others
        "coarse_first": make_record(
            "coarse_first", 25.055, 0.9535, 0.056, decimals={"psnr": 3, "ssim": 4, "lpips": 3}
        ),
        "fine_a": make_record("fine_a", 19.0, 0.92, 0.10),
        # 16.7644 rounds to the same 16.764 as fine_a's start, so it agrees with
        # the coarse row — but the two full-precision rows differ from each other
        "fine_b": make_record(
            "fine_b", 22.0, 0.94, 0.07, start={**START, "psnr": 16.7644}
        ),
    }
    with pytest.raises(ComparabilityError, match="fine_a.*fine_b|fine_b.*fine_a"):
        assemble(make_manifest(rows), records)


def test_the_gate_compares_a_disagreeing_pair_in_the_middle_of_the_manifest():
    """Every pair, not every pair that happens to include an endpoint.

    Found by mutation: the loop bound could be widened from `ordered[index + 1:]`
    to `ordered[index + 2:]` — skipping every adjacent pair — and the whole suite
    still passed, because the one test driving this branch perturbed the *first*
    row, which disagrees with the last as well. Perturbing the middle row instead
    leaves the first and last agreeing, so the disagreement exists only between
    adjacent rows and the gate has to be looking at those to find it.
    """
    manifest, records = (
        make_manifest(
            [
                make_row("null", "null"),
                make_row("imposed16", "imposed", rigidity=16),
                make_row("baseline", "baseline"),
            ]
        ),
        {
            "null": make_record("null", 19.0, 0.92, 0.09),
            "imposed16": make_record("imposed16", 22.0, 0.94, 0.07, num_primitives=23549),
            "baseline": make_record("baseline", 25.0, 0.95, 0.05),
        },
    )
    with pytest.raises(ComparabilityError, match="primitive count"):
        assemble(manifest, records)


def test_the_gate_compares_a_pair_that_is_neither_adjacent_nor_an_endpoint_pair():
    """The other loop bound, and the reason precision makes this testable at all.

    Agreement on the start fingerprint is *not* transitive — that is why the gate is
    pairwise — so a disagreement can be confined to one pair. Here rows 0 and 2 are
    full precision and differ in the fourth decimal, while rows 1 and 3 are console
    lines coarse enough to agree with both. Only the pair (0, 2) disagrees, and a
    loop that walked backwards from each row would compare every other pair and miss
    exactly that one.
    """
    rows = [
        make_row("fine_a", "null"),
        make_row("coarse_b", "imposed", rigidity=4),
        make_row("fine_c", "imposed", rigidity=16),
        make_row("coarse_d", "baseline"),
    ]
    coarse = {"psnr": 3, "ssim": 4, "lpips": 3}
    records = {
        "fine_a": make_record("fine_a", 19.0, 0.92, 0.09),
        "coarse_b": make_record("coarse_b", 21.0, 0.93, 0.08, decimals=coarse),
        # 16.7644 and the shared 16.76434326171875 both round to 16.764, so each
        # agrees with the two coarse rows and only they disagree with each other
        "fine_c": make_record(
            "fine_c", 22.0, 0.94, 0.07, start={**START, "psnr": 16.7644}
        ),
        "coarse_d": make_record("coarse_d", 25.0, 0.95, 0.05, decimals=coarse),
    }
    with pytest.raises(ComparabilityError, match="fine_a.*fine_c|fine_c.*fine_a"):
        assemble(make_manifest(rows), records)


def test_the_gate_raises_rather_than_warning(three_row_case):
    """A silently-wrong comparison produces plausible numbers, which is the worst
    outcome available. Nothing about the gate may be downgraded to a warning."""
    manifest, records = three_row_case
    records["null"] = make_record("null", 19.2, 0.91, 0.09, eval_step=42)
    with pytest.raises(ComparabilityError):
        assemble(manifest, records)


# ── mixed precision ─────────────────────────────────────────────────────────
def test_coarser_source_compares_at_its_own_precision(three_row_case):
    """The baseline is a console line: 3 dp PSNR, 4 dp SSIM, 3 dp LPIPS.

    Its step-0 triple agrees with the full-precision runs only after rounding, so
    the gate must compare at the coarser precision or the real table never builds.
    """
    manifest, records = three_row_case
    table = assemble(manifest, records)  # must not raise
    assert table.row("baseline").metrics["psnr"].decimals == 3


def test_fraction_from_a_coarse_input_carries_its_rounding_interval(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)
    lpips = table.row("imposed16").fractions["lpips"]

    assert not lpips.exact
    assert lpips.low < lpips.value < lpips.high
    # the spec quantifies this one: ~2 percentage points across the interval
    assert (lpips.high - lpips.low) == pytest.approx(0.022, abs=0.002)


def test_rounding_intervals_that_touch_do_not_divide_by_zero():
    """The corner filter in the gap arithmetic, at the only input that needs it.

    Two sources recorded at one decimal and a tenth apart have rounding intervals
    that *meet*: 19.0 spans [18.95, 19.05] and 19.1 spans [19.05, 19.15]. The
    fraction's bounds are found by evaluating it at the corners of those intervals,
    and one corner puts the baseline and the null at the same value — a zero
    denominator, at an input the check upstream cannot see, because that one compares
    the midpoints and they are a tenth apart.

    Found by mutation: the filter that drops the corner could be changed to a
    condition that is always true and nothing failed, because no test had ever put
    two coarse endpoints close enough together. What it prevents is the
    published-cell path raising `ZeroDivisionError` on arithmetic a reader would
    never see coming.
    """
    rows = [
        make_row("null", "null"),
        make_row("imposed16", "imposed", rigidity=16),
        make_row("baseline", "baseline"),
    ]
    tenths = {"psnr": 1}
    records = {
        "null": make_record("null", 19.0, 0.92, 0.09, decimals=tenths),
        "imposed16": make_record("imposed16", 19.05, 0.93, 0.08),
        "baseline": make_record("baseline", 19.1, 0.95, 0.05, decimals=tenths),
    }
    psnr = assemble(make_manifest(rows), records).row("imposed16").fractions["psnr"]

    assert not psnr.exact
    assert psnr.low <= psnr.value <= psnr.high
    for bound in (psnr.low, psnr.high):
        assert math.isfinite(bound), psnr


def test_fraction_from_exact_inputs_is_marked_exact(three_row_case_full_precision):
    manifest, records = three_row_case_full_precision
    table = assemble(manifest, records)
    psnr = table.row("imposed16").fractions["psnr"]
    assert psnr.exact
    assert psnr.low == psnr.high == psnr.value


# ── sign handling on the inverted metric ────────────────────────────────────
def test_lower_lpips_gives_a_higher_fraction():
    """'More is better' must hold uniformly, so no reader inverts a column."""
    rows = [
        make_row("null", "null"),
        make_row("better", "imposed", rigidity=16),
        make_row("worse", "imposed", rigidity=4),
        make_row("baseline", "baseline"),
    ]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.100),
        "better": make_record("better", 22.0, 0.94, 0.070),   # lpips improved more
        "worse": make_record("worse", 21.0, 0.93, 0.090),
        "baseline": make_record("baseline", 25.0, 0.95, 0.050),
    }
    table = assemble(make_manifest(rows), records)
    assert (
        table.row("better").fractions["lpips"].value
        > table.row("worse").fractions["lpips"].value
    )


def test_lpips_worse_than_the_null_gives_a_negative_fraction():
    rows = [
        make_row("null", "null"),
        make_row("regressed", "imposed", rigidity=0.25),
        make_row("baseline", "baseline"),
    ]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.100),
        "regressed": make_record("regressed", 17.9, 0.905, 0.106),  # worse on all three
        "baseline": make_record("baseline", 25.0, 0.95, 0.050),
    }
    table = assemble(make_manifest(rows), records)
    fractions = table.row("regressed").fractions
    assert fractions["lpips"].value < 0
    assert fractions["psnr"].value < 0


# ── the two endpoints have to be distinguishable ────────────────────────────
def test_a_baseline_that_scores_identically_to_the_null_has_no_gap_to_express():
    """The gap fraction's denominator, at zero.

    Every published cell is a fraction of the null→baseline interval, so an interval
    of zero is not a hard case to round carefully — it is a comparison with no
    content. Refusing is the only honest answer, and the refusal is driven here
    because a division that has never been asked to fail is a division nobody knows
    the failure mode of.
    """
    rows = [
        make_row("null", "null"),
        make_row("imposed16", "imposed", rigidity=16),
        make_row("baseline", "baseline"),
    ]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.09),
        "imposed16": make_record("imposed16", 22.0, 0.94, 0.07),
        "baseline": make_record("baseline", 19.0, 0.92, 0.09),  # the null, again
    }
    with pytest.raises(AssemblyError, match="no gap"):
        assemble(make_manifest(rows), records)


# ── manifest failures ───────────────────────────────────────────────────────
def test_a_manifest_declaring_no_rows_at_all_raises():
    """The boundary of "the manifest declares no rows", at zero.

    An empty manifest assembles into an empty table, which is a table that says
    nothing and looks like one that says something.
    """
    with pytest.raises(ManifestError, match="no rows"):
        assemble(make_manifest([]), {})


def test_two_rows_declaring_the_same_key_raise():
    """Two rows bound to one record is a table with a row missing and no gap in it.

    The duplicate check lives in `Manifest.__post_init__` and nothing drove it, so
    its threshold could be raised from "appears more than once" to "more than
    twice" unnoticed. A duplicated key does not fail loudly on its own — the second
    row simply reads the same record as the first — which is exactly the
    plausible-looking wrong table the manifest exists to prevent.
    """
    with pytest.raises(ValueError, match="duplicate manifest keys"):
        make_manifest(
            [
                make_row("null", "null"),
                make_row("imposed16", "imposed", rigidity=16),
                make_row("imposed16", "imposed", rigidity=32),
                make_row("baseline", "baseline"),
            ]
        )


def test_manifest_naming_a_record_that_is_not_supplied_raises(three_row_case):
    manifest, records = three_row_case
    del records["baseline"]
    with pytest.raises(ManifestError, match="baseline"):
        assemble(manifest, records)


def test_missing_baseline_endpoint_raises():
    rows = [make_row("null", "null"), make_row("imposed16", "imposed", rigidity=16)]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.10),
        "imposed16": make_record("imposed16", 22.0, 0.94, 0.07),
    }
    with pytest.raises(ManifestError, match="exactly one 'baseline'"):
        assemble(make_manifest(rows), records)


def test_missing_null_endpoint_raises():
    rows = [make_row("imposed16", "imposed", rigidity=16), make_row("baseline", "baseline")]
    records = {
        "imposed16": make_record("imposed16", 22.0, 0.94, 0.07),
        "baseline": make_record("baseline", 25.0, 0.95, 0.05),
    }
    with pytest.raises(ManifestError, match="exactly one 'null'"):
        assemble(make_manifest(rows), records)


def test_two_baselines_raise():
    rows = [
        make_row("null", "null"),
        make_row("b1", "baseline"),
        make_row("b2", "baseline"),
    ]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.10),
        "b1": make_record("b1", 25.0, 0.95, 0.05),
        "b2": make_record("b2", 25.1, 0.95, 0.05),
    }
    with pytest.raises(ManifestError, match="exactly one 'baseline'"):
        assemble(make_manifest(rows), records)


def test_an_imposed_row_without_a_rigidity_raises():
    rows = [
        make_row("null", "null"),
        make_row("imposed", "imposed"),  # no rigidity declared
        make_row("baseline", "baseline"),
    ]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.10),
        "imposed": make_record("imposed", 22.0, 0.94, 0.07),
        "baseline": make_record("baseline", 25.0, 0.95, 0.05),
    }
    with pytest.raises(ManifestError, match="rigidity"):
        assemble(make_manifest(rows), records)


def test_an_unknown_role_raises():
    rows = [make_row("null", "null"), make_row("x", "sideways"), make_row("b", "baseline")]
    records = {
        "null": make_record("null", 19.0, 0.92, 0.10),
        "x": make_record("x", 22.0, 0.94, 0.07),
        "b": make_record("b", 25.0, 0.95, 0.05),
    }
    with pytest.raises(ManifestError, match="role"):
        assemble(make_manifest(rows), records)


# ── the replicate band, derived rather than typed ───────────────────────────
def test_band_is_derived_from_the_null_family():
    rows = [
        make_row("vanilla", "null"),
        make_row("rho1a", "null_replicate", rigidity=1),
        make_row("rho1b", "null_replicate", rigidity=1),
        make_row("imposed16", "imposed", rigidity=16),
        make_row("baseline", "baseline"),
    ]
    records = {
        "vanilla": make_record("vanilla", 19.277395248413086, 0.9198831915855408, 0.09161172062158585),
        "rho1a": make_record("rho1a", 19.361440658569336, 0.9206077456474304, 0.09082906693220139),
        "rho1b": make_record("rho1b", 19.277315139770508, 0.9201701283454895, 0.09157170355319977),
        "imposed16": make_record("imposed16", 22.953351974487305, 0.9442539215087891, 0.06339161843061447),
        "baseline": make_record("baseline", 25.055, 0.9535, 0.056),
    }
    table = assemble(make_manifest(rows), records)
    assert table.band == pytest.approx(0.084125518798828)
    assert set(table.band_source) == {"vanilla", "rho1a", "rho1b"}


def test_a_lone_null_yields_no_band_and_no_saturation_verdict(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)
    assert table.band is None
    assert table.saturation is None
    assert any("replicate" in n for n in table.notes)


def test_two_null_family_runs_are_the_fewest_that_give_a_band():
    """The boundary of "fewer than two null-family runs, so no band".

    One is tested above and three in the test before it; two is where the rule
    actually changes its answer, and a band derived from exactly two runs is the
    spread between them. Without this the count could be raised to three and nothing
    would notice — and the published sweep would lose its band and its verdict with
    it.
    """
    rows = [
        make_row("vanilla", "null"),
        make_row("rho1a", "null_replicate", rigidity=1),
        make_row("imposed16", "imposed", rigidity=16),
        make_row("baseline", "baseline"),
    ]
    records = {
        "vanilla": make_record("vanilla", 19.0, 0.9198831915855408, 0.09161172062158585),
        "rho1a": make_record("rho1a", 19.25, 0.9206077456474304, 0.09082906693220139),
        "imposed16": make_record("imposed16", 22.0, 0.9442539215087891, 0.06339161843061447),
        "baseline": make_record("baseline", 25.0, 0.9535, 0.056),
    }
    table = assemble(make_manifest(rows), records)
    assert table.band == pytest.approx(0.25)
    assert set(table.band_source) == {"vanilla", "rho1a"}
    assert table.saturation is not None


def test_a_manifest_with_no_imposed_rows_yields_no_saturation_verdict():
    """A band without a sweep to apply it to is not a verdict of "unsaturated".

    The distinction matters because `saturation is None` and `saturation.saturated
    is False` read the same way in a summary and mean opposite things: nothing was
    swept, against a sweep that was and did not turn over.
    """
    rows = [
        make_row("vanilla", "null"),
        make_row("rho1a", "null_replicate", rigidity=1),
        make_row("baseline", "baseline"),
    ]
    records = {
        "vanilla": make_record("vanilla", 19.0, 0.92, 0.09),
        "rho1a": make_record("rho1a", 19.25, 0.92, 0.09),
        "baseline": make_record("baseline", 25.0, 0.95, 0.05),
    }
    table = assemble(make_manifest(rows), records)
    assert table.band == pytest.approx(0.25)  # the band is still derived
    assert table.saturation is None  # but there is nothing to apply it to


def test_saturation_verdict_rides_the_derived_band():
    """The archived sweep, assembled end to end, must report NOT SATURATED."""
    rows = [
        make_row("vanilla", "null"),
        make_row("rho1a", "null_replicate", rigidity=1),
        make_row("rho1b", "null_replicate", rigidity=1),
        make_row("rho025", "imposed", rigidity=0.25),
        make_row("rho4", "imposed", rigidity=4),
        make_row("rho16", "imposed", rigidity=16),
        make_row("baseline", "baseline"),
    ]
    records = {
        "vanilla": make_record("vanilla", 19.277395248413086, 0.9198831915855408, 0.09161172062158585),
        "rho1a": make_record("rho1a", 19.361440658569336, 0.9206077456474304, 0.09082906693220139),
        "rho1b": make_record("rho1b", 19.277315139770508, 0.9201701283454895, 0.09157170355319977),
        "rho025": make_record("rho025", 17.906381607055664, 0.9052637219429016, 0.10588297992944717),
        "rho4": make_record("rho4", 22.1044979095459, 0.9381635785102844, 0.0696517825126648),
        "rho16": make_record("rho16", 22.953351974487305, 0.9442539215087891, 0.06339161843061447),
        "baseline": make_record("baseline", 25.055, 0.9535, 0.056),
    }
    table = assemble(make_manifest(rows), records)
    assert table.saturation is not None
    assert not table.saturation.saturated
    assert table.saturation.continue_at == 32
    assert table.selected_row is None  # nothing may be reported yet


# ── provenance ──────────────────────────────────────────────────────────────
def test_every_row_carries_provenance(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)
    for row in table.rows:
        assert row.provenance
        assert row.key in row.provenance
