"""Tests for the assembler — the one seam.

External behaviour only: given these records and this manifest, this table or this
failure comes out. Negative cases carry as much weight as positive ones, because a
gate nothing can fail is not evidence.
"""

import pytest

from conftest import START, exact, make_manifest, make_record, make_row
from plan1.assemble import ComparabilityError, ManifestError, assemble


# ── the positive case ───────────────────────────────────────────────────────
def test_well_formed_rows_produce_the_published_table(three_row_case):
    manifest, records = three_row_case
    table = assemble(manifest, records)

    assert table.eval_step == 501
    assert table.num_primitives == 23548
    assert [r.key for r in table.rows] == ["null", "imposed16", "baseline"]

    # the shared start is printed in the table, so a reader can verify at a glance
    assert table.start["psnr"].value == pytest.approx(16.76434326171875)

    # the parent spec's published table: 63.6% / 72.6% / 79.2%, with the SSIM cell
    # corrected to 72.5% (see the next test)
    imposed = table.row("imposed16")
    assert imposed.fractions["psnr"].value == pytest.approx(0.6362423, abs=1e-7)
    assert imposed.fractions["ssim"].value == pytest.approx(0.7249567, abs=1e-7)
    assert imposed.fractions["lpips"].value == pytest.approx(0.7924386, abs=1e-7)
    assert [round(imposed.fractions[m].value * 100, 1) for m in ("psnr", "lpips")] == [
        63.6,
        79.2,
    ]


def test_ssim_fraction_is_725_not_the_published_726(three_row_case):
    """The parent spec's 72.6% came from rounding inputs before dividing.

    plan-1-comparison-assembly-spec.md "Further Notes" corrects the cell to 72.5%.
    A correct assembler must produce the corrected value, so this pins it.
    """
    manifest, records = three_row_case
    table = assemble(manifest, records)
    assert round(table.row("imposed16").fractions["ssim"].value * 100, 1) == 72.5


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
    records["baseline"] = make_record(
        "baseline",
        25.055,
        0.9535,
        0.056,
        decimals={"psnr": 3, "ssim": 4, "lpips": 3},
    )
    table = assemble(manifest, records)  # must not raise
    assert table.row("baseline").metrics["psnr"].decimals == 3


def test_fraction_from_a_coarse_input_carries_its_rounding_interval(three_row_case):
    manifest, records = three_row_case
    records["baseline"] = make_record(
        "baseline",
        25.055,
        0.9535,
        0.056,
        decimals={"psnr": 3, "ssim": 4, "lpips": 3},
    )
    table = assemble(manifest, records)
    lpips = table.row("imposed16").fractions["lpips"]

    assert not lpips.exact
    assert lpips.low < lpips.value < lpips.high
    # the spec quantifies this one: ~2 percentage points across the interval
    assert (lpips.high - lpips.low) == pytest.approx(0.022, abs=0.002)


def test_fraction_from_exact_inputs_is_marked_exact(three_row_case):
    manifest, records = three_row_case  # baseline built without declared decimals
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


# ── manifest failures ───────────────────────────────────────────────────────
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
