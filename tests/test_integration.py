"""End-to-end against the real archive: manifest -> records -> table.

These are the tests that read real evidence rather than fixtures — they are what
proves the readers, the gate and the arithmetic work on the archived runs and not
only on numbers made up for the purpose. The evidence is vendored under
`evidence/`, so they run on a bare clone. They previously resolved a checkout
outside this repository and skipped in its absence, which quietly removed all 18
of them on every machine but one.

**Two worlds, both live.** ``real_table`` is what the manifest publishes today: the
baseline bound to its own recovered statistics record, every input at full
precision. ``console_baseline_table`` is the branch `plan1_prereg.md` §7 declared
as its fallback and did not take — the baseline known only from the 2026-07-22
console line. The second is kept because the branch was declared, because it is
the only thing that exercises the console-log reader against a real file, and
because the intervals quoted in the verdict are read out of it rather than typed.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from conftest import PARENT_CELLS, overlaps
from plan1.assemble import assemble
from plan1.manifest import load_manifest, load_records
from plan1.provenance import EVIDENCE_ROOT
from plan1.records import METRICS
from plan1.render import render_markdown

MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "penguin_deformsplat.toml"

#: The vendored evidence base, in the repository. This was a checkout outside it,
#: and its absence silently removed all 18 tests below.
ARCHIVE = EVIDENCE_ROOT

#: The console line the baseline row was bound to before preflight recovered the
#: run's own statistics record. It survives in the archive, so the superseded world
#: can still be assembled from a parsed file.
SUPERSEDED_CONSOLE_LOG = "cluster/spike_logs/phase3_run_console.log"

if not (ARCHIVE / "cluster" / "rho_probe_evidence").is_dir():
    raise FileNotFoundError(
        f"the nine archived run directories are missing under {ARCHIVE}. This is "
        f"a bug, not a reason to skip — they are vendored here and recorded in "
        f"evidence/PROVENANCE.toml. This guard used to be a skipif, and it was "
        f"quietly removing all 18 of these tests on every machine but one."
    )


@pytest.fixture(scope="module")
def real_table():
    manifest = load_manifest(MANIFEST)
    return assemble(manifest, load_records(manifest))


@pytest.fixture(scope="module")
def console_baseline_table():
    """The same comparison with the baseline rebound to the superseded console line.

    Only the baseline row's *source* changes. Every other row, the gate, the band
    and the rule are the manifest's own.
    """
    manifest = load_manifest(MANIFEST)
    rows = tuple(
        replace(row, kind="console_log", path=SUPERSEDED_CONSOLE_LOG)
        if row.role == "baseline"
        else row
        for row in manifest.rows
    )
    manifest = replace(manifest, rows=rows)
    return assemble(manifest, load_records(manifest))


# ── the gate, on the real rows ──────────────────────────────────────────────
def test_the_real_rows_pass_the_comparability_gate(real_table):
    """All nine rows began from the same state — the two saturation runs included,
    which is what licenses comparing them against the seven that preceded them."""
    assert real_table.num_primitives == 23548
    assert real_table.eval_step == 501
    assert len(real_table.rows) == 9


def test_the_console_baseline_still_passes_the_gate(console_baseline_table):
    """The console line agrees with the full-precision runs only after rounding to
    its own display precision, so this is the mixed-precision path end to end."""
    assert len(console_baseline_table.rows) == 9
    assert console_baseline_table.num_primitives == 23548


# ── the baseline row, in each world ─────────────────────────────────────────
def test_the_baseline_is_read_at_full_precision(real_table):
    baseline = real_table.row("baseline")
    assert baseline.metrics["psnr"].value == pytest.approx(25.054527282714844)
    assert all(baseline.metrics[m].exact for m in METRICS)
    assert "baseline_penguin_0217_0239" in baseline.provenance


def test_the_baseline_is_read_at_display_precision(console_baseline_table):
    baseline = console_baseline_table.row("baseline")
    assert baseline.metrics["psnr"].value == pytest.approx(25.055)
    assert baseline.metrics["psnr"].decimals == 3
    assert baseline.metrics["ssim"].decimals == 4
    assert baseline.metrics["lpips"].decimals == 3
    assert "phase3_run_console.log:66" in baseline.provenance


def test_the_recovered_record_rounds_to_the_console_line_it_supersedes(
    real_table, console_baseline_table
):
    """plan1_prereg.md §7's qualifying condition, asserted across the two worlds.

    This is what makes the rebinding a sharpening of the same run rather than a
    substitution of a different one — and it is checked against both parsed
    sources, not against a typed triple.
    """
    recovered = real_table.row("baseline").metrics
    console = console_baseline_table.row("baseline").metrics
    for metric in METRICS:
        assert recovered[metric].agrees_with(console[metric])


# ── the published fractions ─────────────────────────────────────────────────
def test_the_archived_fractions_are_the_published_table(real_table):
    """What the table publishes today: 63.6% / 72.6% / 80.4%, all exact."""
    fractions = real_table.row("rho16").fractions
    assert [round(fractions[m].value * 100, 1) for m in METRICS] == [63.6, 72.6, 80.4]
    for fraction in fractions.values():
        assert fraction.exact
        assert fraction.low == fraction.high == fraction.value


def test_the_console_baseline_world_yields_the_superseded_fractions(
    console_baseline_table,
):
    """The same rows under the console line — the branch that was not taken.

    Renamed from `test_the_archived_fractions_reproduce_the_published_table`. Its
    numbers are right for this world, but its old title asserted something the
    published table no longer says: SSIM here resolves to 72.5%, and the published
    table reads 72.6%. Neither is a correction of the other — see the retraction in
    `docs/specs/plan-1-comparison-assembly-spec.md`.
    """
    fractions = console_baseline_table.row("rho16").fractions
    assert [round(fractions[m].value * 100, 1) for m in METRICS] == [63.6, 72.5, 79.2]


def test_the_console_baseline_intervals_cover_the_parent_cells(console_baseline_table):
    """The retraction's central fact, read out of parsed archive files.

    Every one of the three intervals the assembler published under the console
    baseline overlaps the parent spec's corresponding cell. No correction of any of
    them was ever licensed — including the SSIM cell one was claimed for.
    """
    fractions = console_baseline_table.row("rho16").fractions
    for metric in METRICS:
        assert overlaps(fractions[metric], PARENT_CELLS[metric]), metric


def test_the_console_baseline_intervals_cover_the_values_later_recovered(
    real_table, console_baseline_table
):
    """All three. The machinery was correct throughout; only the reading was wrong.

    The LPIPS value sits about a thousandth of a percentage point below its upper
    bound. That is close, and it is not a miss: the interval stated in advance the
    range a sharper reading could occupy, and the sharper reading occupied it.
    """
    recovered = real_table.row("rho16").fractions
    published = console_baseline_table.row("rho16").fractions
    for metric in METRICS:
        low, high = published[metric].low, published[metric].high
        assert low <= recovered[metric].value <= high, metric


def test_every_fraction_carries_an_interval_from_the_console_baseline(
    console_baseline_table,
):
    """The baseline is a console line, so no fraction derived from it is exact."""
    for fraction in console_baseline_table.row("rho16").fractions.values():
        assert not fraction.exact
        assert fraction.low < fraction.value < fraction.high


def test_the_lpips_interval_is_worth_about_two_percentage_points(
    console_baseline_table,
):
    """Reporting that fraction to one decimal would claim precision the input does
    not have. Recovering the run's own record is what removed the problem; before
    that it was the reason no cell could be published as a point."""
    assert console_baseline_table.row("rho16").fractions["lpips"].spread == pytest.approx(
        0.022, abs=0.002
    )


# ── the band and the rule ───────────────────────────────────────────────────
def test_the_band_is_derived_from_the_three_null_runs(real_table):
    assert real_table.band == pytest.approx(0.084125518798828)
    assert set(real_table.band_source) == {"vanilla", "rho1a", "rho1b"}


def test_the_extended_sweep_saturates_and_selects_rho16(real_table):
    """The two saturation runs turned the curve over, so the pre-registered rule
    returns SATURATED and selects the smallest rigidity inside the band."""
    verdict = real_table.saturation
    assert verdict.saturated
    assert verdict.continue_at is None
    assert real_table.selected_row.key == "rho16"
    assert "turned over" in verdict.reason


def test_the_rule_selects_the_same_row_in_either_precision_world(
    real_table, console_baseline_table
):
    """The selector reads PSNR off the imposed rows only, so rebinding the baseline
    cannot move it. Asserted rather than assumed."""
    assert (
        console_baseline_table.selected_row.key == real_table.selected_row.key == "rho16"
    )


# ── the rendered table ──────────────────────────────────────────────────────
def test_the_rendered_table_publishes_the_gap_fraction_at_the_selected_row(real_table):
    text = render_markdown(real_table)
    assert "**Saturation rule — SATURATED.**" in text
    assert "fraction of the gap recovered" in text
    assert "| 63.6% | 72.6% | 80.4% |" in text
    # the limitations that must travel with the claim
    assert "code inspection" in text
    assert "assumption, not a measurement" in text
    assert "is not a goal and is not claimed" in text


def test_the_rendered_table_never_prints_a_digit_the_source_lacks(
    console_baseline_table,
):
    """The console baseline records LPIPS as 0.056; printing 0.0560 fabricates a
    digit. The recovered record has the fourth decimal, so this only bites here."""
    text = render_markdown(console_baseline_table)
    assert "| 0.056 |" in text
    assert "0.0560" not in text


def test_the_rendered_fraction_shows_its_interval_when_the_input_is_coarse(
    console_baseline_table,
):
    text = render_markdown(console_baseline_table)
    assert "79.2% [78.1–80.4%]" in text


def test_a_manifest_pointing_at_a_missing_record_raises(tmp_path):
    manifest_text = MANIFEST.read_text().replace(
        "penguin_vanilla", "penguin_does_not_exist"
    )
    broken = tmp_path / "broken.toml"
    # roots resolve against the manifest's own directory, so point this one back
    broken.write_text(
        manifest_text.replace('archive = "../evidence"', f'archive = "{ARCHIVE}"')
    )
    with pytest.raises(FileNotFoundError, match="no such statistics file"):
        load_records(load_manifest(broken))
