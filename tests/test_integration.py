"""End-to-end against the real archive: manifest -> records -> table.

These are the only tests that read outside the repository. They skip cleanly when
the archive is absent, so the repo stays reviewable as one unit, but when it is
present they are what proves the readers, the gate and the arithmetic work on the
actual evidence rather than only on fixtures.
"""

from pathlib import Path

import pytest

from plan1.assemble import assemble
from plan1.manifest import load_manifest, load_records
from plan1.render import render_markdown

MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "penguin_deformsplat.toml"
ARCHIVE = Path(__file__).resolve().parents[2] / "3D"

pytestmark = pytest.mark.skipif(
    not (ARCHIVE / "cluster" / "rho_probe_evidence").is_dir(),
    reason=f"archive run evidence not present under {ARCHIVE}",
)


@pytest.fixture(scope="module")
def real_table():
    manifest = load_manifest(MANIFEST)
    return assemble(manifest, load_records(manifest))


def test_the_real_rows_pass_the_comparability_gate(real_table):
    """All seven rows began from the same state — including the console-line
    baseline, which agrees only after rounding to its own display precision."""
    assert real_table.num_primitives == 23548
    assert real_table.eval_step == 501
    assert len(real_table.rows) == 7


def test_the_baseline_is_read_at_display_precision(real_table):
    baseline = real_table.row("baseline")
    assert baseline.metrics["psnr"].value == pytest.approx(25.055)
    assert baseline.metrics["psnr"].decimals == 3
    assert baseline.metrics["ssim"].decimals == 4
    assert baseline.metrics["lpips"].decimals == 3
    assert "phase3_run_console.log:66" in baseline.provenance


def test_the_archived_fractions_reproduce_the_published_table(real_table):
    """The parent spec elevates exact reproduction to a correctness check: a
    mismatch is defined there as evidence the assembly is reading the wrong runs.

    PSNR and LPIPS match its published cells. SSIM resolves to 72.5%, not the
    published 72.6% — that cell came from rounding the inputs to four decimals
    before dividing, and Plan 1 corrects it explicitly.
    """
    fractions = real_table.row("rho16").fractions
    assert round(fractions["psnr"].value * 100, 1) == 63.6
    assert round(fractions["ssim"].value * 100, 1) == 72.5
    assert round(fractions["lpips"].value * 100, 1) == 79.2


def test_every_fraction_carries_an_interval_from_the_console_baseline(real_table):
    """The baseline is a console line, so no fraction derived from it is exact."""
    for fraction in real_table.row("rho16").fractions.values():
        assert not fraction.exact
        assert fraction.low < fraction.value < fraction.high


def test_the_lpips_interval_is_worth_about_two_percentage_points(real_table):
    """Reporting that fraction to one decimal would claim precision the input
    does not have — which is the defect this whole deliverable exists to fix."""
    assert real_table.row("rho16").fractions["lpips"].spread == pytest.approx(
        0.022, abs=0.002
    )


def test_the_band_is_derived_from_the_three_null_runs(real_table):
    assert real_table.band == pytest.approx(0.084125518798828)
    assert set(real_table.band_source) == {"vanilla", "rho1a", "rho1b"}


def test_the_archived_sweep_is_not_saturated_so_no_row_is_reported(real_table):
    """The pre-registered rule is what demands the rho=32 and rho=64 runs."""
    assert not real_table.saturation.saturated
    assert real_table.saturation.continue_at == 32
    assert real_table.selected_row is None


def test_the_rendered_table_publishes_no_gap_fraction_while_unsaturated(real_table):
    text = render_markdown(real_table)
    assert "NOT SATURATED" in text
    assert "fraction of the gap recovered" not in text
    # the limitations that must travel with the claim
    assert "code inspection" in text
    assert "assumption, not a measurement" in text


def test_the_rendered_table_never_prints_a_digit_the_source_lacks(real_table):
    """The baseline LPIPS is recorded as 0.056; printing 0.0560 fabricates a digit."""
    text = render_markdown(real_table)
    assert "| 0.056 |" in text
    assert "0.0560" not in text


def test_a_manifest_pointing_at_a_missing_record_raises(tmp_path):
    manifest_text = MANIFEST.read_text().replace(
        "penguin_vanilla", "penguin_does_not_exist"
    )
    broken = tmp_path / "broken.toml"
    # roots resolve against the manifest's own directory, so point this one back
    broken.write_text(manifest_text.replace('archive = "../../3D"', f'archive = "{ARCHIVE}"'))
    with pytest.raises(FileNotFoundError, match="no such statistics file"):
        load_records(load_manifest(broken))
