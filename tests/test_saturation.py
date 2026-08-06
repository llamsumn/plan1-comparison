"""Tests for the saturation rule — the pre-registered selector.

The rule (plan1_prereg.md §3): the reported setting is the *smallest* rigidity whose
PSNR falls within the replicate band of the sweep maximum. If the largest swept
rigidity is still gaining more than the band over its predecessor, the curve has not
saturated and no row may be reported.

Behaviour only — these drive synthetic sweeps and assert which row comes out.
"""

import pytest

from plan1.saturation import SweepPoint, select_saturated_row


def sweep(*pairs):
    return [SweepPoint(rigidity=r, psnr=p, key=f"rho{r:g}") for r, p in pairs]


# ── the four cases the spec names ───────────────────────────────────────────
def test_monotone_saturating_curve_returns_smallest_row_inside_the_band():
    # 4, 8 and 16 all sit within 0.1 dB of the 12.96 maximum; 4 is the smallest.
    v = select_saturated_row(
        sweep((1, 10.00), (2, 12.00), (4, 12.90), (8, 12.95), (16, 12.96)), band=0.1
    )
    assert v.saturated
    assert v.selected.rigidity == 4
    assert v.maximum.rigidity == 16


def test_curve_that_turns_over_does_not_report_the_over_stiffened_tail():
    # the tail (rho=32) is the *last* row but it has fallen off the maximum.
    v = select_saturated_row(
        sweep((1, 10.0), (4, 12.0), (16, 12.5), (32, 11.0)), band=0.1
    )
    assert v.saturated
    assert v.selected.rigidity == 16


def test_unsaturated_curve_triggers_continuation_and_reports_no_row():
    v = select_saturated_row(sweep((1, 10.0), (4, 14.0), (16, 18.0)), band=0.1)
    assert not v.saturated
    assert v.selected is None
    assert v.continue_at == 32
    assert v.last_gain == pytest.approx(4.0)


def test_ties_inside_the_band_resolve_to_the_smallest_rigidity():
    # the maximum is at 16, but 4 and 64 are also inside the band; 4 wins.
    v = select_saturated_row(
        sweep((1, 10.00), (4, 12.50), (16, 12.52), (64, 12.51)), band=0.1
    )
    assert v.saturated
    assert v.selected.rigidity == 4
    assert v.maximum.rigidity == 16


# ── the declared continuation ladder ────────────────────────────────────────
def test_continuation_walks_the_declared_ladder():
    for largest, expected in ((16, 32), (32, 64), (64, 128), (128, 256)):
        v = select_saturated_row(sweep((1, 10.0), (largest, 30.0)), band=0.1)
        assert not v.saturated
        assert v.continue_at == expected, f"largest={largest}"


def test_hard_stop_at_256_reports_a_finding_rather_than_continuing():
    v = select_saturated_row(sweep((64, 20.0), (256, 30.0)), band=0.1)
    assert not v.saturated
    assert v.selected is None
    assert v.continue_at is None          # the ladder is exhausted
    assert v.hard_stop_reached
    assert "did not saturate" in v.reason


# ── degenerate inputs ───────────────────────────────────────────────────────
def test_empty_sweep_raises():
    with pytest.raises(ValueError, match="at least one"):
        select_saturated_row([], band=0.1)


def test_single_point_sweep_cannot_demonstrate_saturation():
    v = select_saturated_row(sweep((16, 22.9)), band=0.1)
    assert not v.saturated
    assert v.continue_at == 32
    assert "single-point" in v.reason


def test_single_point_sweep_at_the_hard_stop_still_reports():
    """No predecessor *and* no rung left — the reason cannot cite a gain."""
    v = select_saturated_row(sweep((256, 30.0)), band=0.1)
    assert not v.saturated
    assert v.selected is None
    assert v.continue_at is None
    assert v.hard_stop_reached
    assert "exhausted" in v.reason


def test_band_must_be_positive():
    with pytest.raises(ValueError, match="band"):
        select_saturated_row(sweep((1, 10.0), (4, 12.0)), band=0.0)


def test_duplicate_rigidity_values_raise():
    with pytest.raises(ValueError, match="duplicate"):
        select_saturated_row(sweep((1, 10.0), (1, 10.5)), band=0.1)


# ── how the verdict describes what it decided ───────────────────────────────
# The predicate is pre-registered and untouched. Only the SENTENCE changes, and
# only where the old one was arithmetic nonsense: a curve that has fallen off its
# maximum was described as "gaining -1.0889 dB … within the band".
def test_a_turned_over_curve_is_described_as_turning_over():
    v = select_saturated_row(
        sweep((1, 10.0), (4, 12.0), (16, 12.5), (32, 11.0)), band=0.1
    )
    assert v.saturated
    assert "turned over" in v.reason
    assert "falls 1.5000 dB below its predecessor" in v.reason
    # the sentence that made this unreadable: a negative quantity presented as a
    # gain, and a fall of 1.5 dB presented as sitting inside a 0.1 dB band
    assert "gains -" not in v.reason
    assert "within the 0.1000 dB band" not in v.reason


def test_a_flattening_curve_is_still_described_as_a_gain_within_the_band():
    """The other branch is untouched — a curve that flattens really did gain."""
    v = select_saturated_row(sweep((1, 10.00), (4, 12.90), (16, 12.95)), band=0.1)
    assert v.saturated
    assert "gains 0.0500 dB over its predecessor, within the 0.1000 dB band" in v.reason
    assert "turned over" not in v.reason


def test_a_curve_that_exactly_flatlines_reads_as_a_gain_not_a_turnover():
    """Zero is not a fall. The branch is on the sign, and 0.0 is not negative."""
    v = select_saturated_row(sweep((1, 10.0), (4, 12.0), (16, 12.0)), band=0.1)
    assert v.saturated
    assert v.last_gain == 0.0
    assert "turned over" not in v.reason


def test_the_wording_change_cannot_move_which_row_is_reported():
    """The decision pin, over the real sweep, at the real band.

    plan1_prereg.md §3 fixes the RULE, not the sentence describing it. This asserts
    the part that is fixed, so a prose edit provably could not move it.
    """
    v = select_saturated_row(
        sweep(
            (0.25, 17.906381607055664),
            (4, 22.1044979095459),
            (16, 22.953351974487305),
            (32, 21.82762336730957),
            (64, 20.738685607910156),
        ),
        band=0.08412551879882812,
    )
    assert v.saturated
    assert v.selected.rigidity == 16
    assert v.maximum.rigidity == 16
    assert v.continue_at is None
    assert [p.rigidity for p in v.within_band] == [16]
    assert v.last_gain == pytest.approx(-1.0889377593994141)


# ── regression guard on the pre-registered claim ────────────────────────────
def test_archived_sweep_as_it_stands_is_not_saturated():
    """plan1_prereg.md §3.2 records that the rule was already failing when written.

    If this ever passes, the pre-registration's stated justification for the rho=32
    and rho=64 runs has silently changed.
    """
    v = select_saturated_row(
        sweep(
            (0.25, 17.906381607055664),
            (1, 19.361440658569336),
            (4, 22.1044979095459),
            (16, 22.953351974487305),
        ),
        band=0.08412551879882812,
    )
    assert not v.saturated
    assert v.continue_at == 32
    assert v.last_gain == pytest.approx(0.8488540649414062)
