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
