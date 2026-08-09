"""The renderer's optional sections, present and absent.

`render_markdown` builds five things conditionally: the selected row's gap
fraction, the saturation verdict, the "no fraction is published" warning, the
full disclosed sweep, and the replicate band. The published table has all five,
so every existing test renders a document where every condition is true and none
of the `else` paths runs.

That asymmetry matters more here than it would elsewhere, because the conditions
are not decoration. **The warning at the centre of this module is the repository's
central discipline as a paragraph of output**: when the sweep has not saturated,
no gap-recovered fraction may be published, and the rule that decides this was
declared before the runs. A renderer that dropped that paragraph would produce a
document that looks complete and is missing the sentence that says why the number
a reader is looking for is not there.

So both directions are tested: a table with nothing optional in it renders
without any of the five, and an unsaturated table renders the refusal.
"""

import pytest

from plan1.assemble import ComparisonTable, TableRow
from plan1.records import Measurement
from plan1.render import render_markdown
from plan1.saturation import SaturationVerdict, SweepPoint

TRIPLE = {
    "psnr": Measurement(20.0),
    "ssim": Measurement(0.9),
    "lpips": Measurement(0.1),
}


def bare_row(key, role, rigidity=None):
    return TableRow(
        key=key,
        label=key,
        role=role,
        rigidity=rigidity,
        information="—",
        metrics=dict(TRIPLE),
        provenance=f"fixture record {key}",
    )


def table(*, rows, saturation=None, band=None, band_source=()):
    return ComparisonTable(
        asset="penguin_0217_0239",
        manifest_source="fixture://manifest",
        assembled="2026-08-08",
        eval_step=501,
        num_primitives=23548,
        start=dict(TRIPLE),
        rows=tuple(rows),
        band=band,
        band_source=band_source,
        saturation=saturation,
        notes=("a limitation, stated where the claim is made",),
    )


@pytest.fixture
def minimal():
    """One row, no sweep, no verdict, no replicates. Everything optional absent."""
    return table(rows=[bare_row("baseline", "baseline")])


@pytest.fixture
def unsaturated():
    """A sweep the rule refused to select from. `selected=None` is what makes it a
    refusal rather than an omission."""
    verdict = SaturationVerdict(
        saturated=False,
        selected=None,
        maximum=SweepPoint(rigidity=16.0, psnr=22.95, key="imposed16"),
        band=0.05,
        last_gain=0.9,
        continue_at=32.0,
        hard_stop_reached=False,
        reason="the last gain of 0.9 dB is outside the replicate band of 0.05 dB",
    )
    return table(
        rows=[bare_row("baseline", "baseline"), bare_row("imposed16", "imposed", 16.0)],
        saturation=verdict,
    )


# ── everything optional absent ──────────────────────────────────────────────
def test_a_table_with_nothing_optional_still_renders(minimal):
    """The parts that are never conditional: the title, the byline, the header
    row and the limitations. If the renderer only worked on a complete table it
    would be untestable on anything but the published one."""
    text = render_markdown(minimal)

    assert text.startswith("# penguin_0217_0239 —")
    assert "| PSNR | SSIM | LPIPS |" in text
    assert "## Limitations" in text
    assert "a limitation, stated where the claim is made" in text


def test_no_gap_fraction_line_appears_when_no_row_was_selected(minimal):
    assert "fraction of the gap recovered" not in render_markdown(minimal)


def test_no_saturation_verdict_appears_when_the_rule_did_not_run(minimal):
    assert "Saturation rule" not in render_markdown(minimal)


def test_no_sweep_section_appears_when_nothing_was_swept(minimal):
    assert "Full imposed sweep" not in render_markdown(minimal)


def test_no_replicate_band_appears_when_the_null_was_run_once(minimal):
    """`band` is `None` on this table, and the section formats it with `:.4f` —
    so a renderer that emitted the section unconditionally would not print a
    wrong number here, it would raise. Worth knowing which."""
    assert "replicate band" not in render_markdown(minimal)


def test_a_single_null_row_is_still_not_a_family(minimal):
    """The boundary of the condition above. One null row is not "run more than
    once", so the section stays out."""
    one_null = table(rows=[bare_row("baseline", "baseline"), bare_row("null", "null")])
    assert "was run" not in render_markdown(one_null)


# ── the refusal, printed ────────────────────────────────────────────────────
def test_an_unsaturated_sweep_prints_the_verdict_and_the_refusal(unsaturated):
    """The paragraph this module exists for. Three things have to be in it: that
    the rule ran, that it did not saturate, and that the rule was declared before
    the runs — the last is what makes the absence of a number a result rather
    than a gap in the work."""
    text = render_markdown(unsaturated)

    assert "**Saturation rule — NOT SATURATED.**" in text
    assert "outside the replicate band" in text
    assert "No gap-recovered fraction is published while the sweep is unsaturated" in text
    assert "declared before the runs" in text


def test_an_unsaturated_sweep_publishes_no_fraction(unsaturated):
    """The refusal as an assertion about the output rather than about the prose:
    whatever the paragraph says, the number must not be in the document."""
    assert "fraction of the gap recovered" not in render_markdown(unsaturated)


def test_an_unsaturated_sweep_still_discloses_the_full_sweep(unsaturated):
    """Refusing to select is not refusing to show. The sweep is printed either
    way, which is what makes the selection disclosed rather than hidden."""
    text = render_markdown(unsaturated)

    assert "Full imposed sweep" in text
    assert "selection is disclosed, not hidden" in text
    assert "| 16 | imposed |" in text
