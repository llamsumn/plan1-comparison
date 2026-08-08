"""Tests for the saturation rule — the pre-registered selector.

The rule (plan1_prereg.md §3): the reported setting is the *smallest* rigidity whose
PSNR falls within the replicate band of the sweep maximum. If the largest swept
rigidity is still gaining more than the band over its predecessor, the curve has not
saturated and no row may be reported.

Behaviour only — these drive synthetic sweeps and assert which row comes out.

**Both of the rule's comparisons are inclusive, and until now nothing said so.**
Every sweep below sat comfortably inside or outside the band, so `>=` could be
changed to `>` and `<=` to `<` and all 627 tests still passed — measured, not
supposed. Those two characters are the entire content of the rule at the point where
it decides: *within* the band means at the edge as well as inside it, and a curve
that has stopped gaining includes one that gained exactly the band. So the two
thresholds are now driven at the boundary value itself and one float either side of
it, in the section marked below.

**Each of them was watched failing first.** This project has shipped two guards that
could not fail, so a boundary assertion — the kind most likely to be written to pass
— is not trusted here until the wrong implementation has been seen failing it. What
was driven, and which test caught it:

| the source, made wrong | the test that failed |
|---|---|
| `last_gain <= band` → `<` | `test_a_gain_of_exactly_the_band_counts_as_saturated` |
| `p.psnr >= maximum.psnr - band` → `>` | `test_a_row_exactly_on_the_band_edge_is_inside_the_band` |
| `len(ordered) >= 2` → `> 2` | `test_two_points_are_the_fewest_that_can_demonstrate_saturation` |
| `hard_stop_reached=False` → `True`, saturated path | `test_the_hard_stop_flag_is_false_on_the_saturated_path` |
| `hard_stop = continue_at is None` → `is not None` | `test_the_hard_stop_flag_is_false_while_the_ladder_still_has_a_rung` |
| `if not band > 0.0` → `if band <= 0.0` | `test_a_nan_band_is_refused_rather_than_silently_accepted` |

The mapping is recorded rather than the pass counts, because a total goes stale the
moment a test is added and this table does not.
"""

import math

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


# ── the two thresholds, at the boundary value itself ────────────────────────
# The pre-registration says "within the replicate band". Both comparisons that
# implement it are inclusive, and each is pinned here at the boundary and at the
# nearest float on the wrong side of it — which is as close to the edge as a double
# can be driven, so nothing is left between the two cases for a change to hide in.
def test_a_gain_of_exactly_the_band_counts_as_saturated():
    """`last_gain <= band`, at equality. 10.5 - 10.0 is exactly 0.5 in binary."""
    v = select_saturated_row(sweep((1, 10.0), (4, 10.5)), band=0.5)
    assert v.last_gain == 0.5
    assert v.saturated, "a gain of exactly the band is within it, not outside it"
    assert v.selected.rigidity == 1


def test_a_gain_one_float_above_the_band_is_not_saturated():
    """The other side of the same equality, one ulp away.

    The gain is held at exactly 0.5 and the *band* is stepped down instead, because
    stepping the PSNR up by one ulp at magnitude 10 would round straight back to 10.5
    and quietly test nothing.
    """
    v = select_saturated_row(
        sweep((1, 10.0), (4, 10.5)), band=math.nextafter(0.5, 0.0)
    )
    assert v.last_gain == 0.5
    assert not v.saturated
    assert v.selected is None


def test_a_row_exactly_on_the_band_edge_is_inside_the_band():
    """`psnr >= maximum - band`, at equality — the comparison that picks the row.

    The maximum is 12.5 and the band 0.5, so the edge is exactly 12.0 and rho=4 sits
    on it. Inclusive, rho=4 is reported; exclusive, the reported row jumps to rho=16.
    This is the rule that selects the published row, so the two characters between
    those outcomes are the whole of it.
    """
    v = select_saturated_row(
        sweep((1, 8.0), (4, 12.0), (16, 12.5), (32, 12.5)), band=0.5
    )
    assert v.saturated
    assert v.maximum.psnr == 12.5
    assert v.selected.rigidity == 4
    assert [p.rigidity for p in v.within_band] == [4, 16, 32]


def test_a_row_one_float_below_the_band_edge_is_outside_it():
    """The same sweep with rho=4 stepped down by a single ulp: it drops out."""
    v = select_saturated_row(
        sweep(
            (1, 8.0),
            (4, math.nextafter(12.0, -math.inf)),
            (16, 12.5),
            (32, 12.5),
        ),
        band=0.5,
    )
    assert v.saturated
    assert v.selected.rigidity == 16
    assert [p.rigidity for p in v.within_band] == [16, 32]


def test_two_points_are_the_fewest_that_can_demonstrate_saturation():
    """`len(ordered) >= 2`, at the boundary.

    One point cannot saturate because there is nothing to have gained over; two
    can, and the smaller number is the interesting one because the rule is about a
    curve turning over and two points are the fewest that make a curve.
    """
    two = select_saturated_row(sweep((1, 10.0), (4, 10.25)), band=0.5)
    assert two.saturated
    assert two.selected.rigidity == 1

    one = select_saturated_row(sweep((4, 10.25)), band=0.5)
    assert not one.saturated


# ── the hard-stop flag, on every branch that sets it ────────────────────────
# Three branches set it and only one was asserted. A flag that is checked in one
# place and written in three is a flag that means something different in each.
def test_the_hard_stop_flag_is_false_on_the_saturated_path():
    """Saturating *at* the last rung is not a hard stop — it is the answer.

    The hard stop is the finding "we ran out of ladder without saturating", and it
    has to stay distinguishable from "we saturated, and there happened to be no rung
    left". Driven at rho=256, the exhausting rung, so the two are told apart on the
    only input where they could be confused.
    """
    v = select_saturated_row(sweep((1, 10.0), (256, 10.25)), band=0.5)
    assert v.saturated
    assert v.hard_stop_reached is False
    assert v.continue_at is None
    assert "did not saturate" not in v.reason


def test_the_hard_stop_flag_is_false_while_the_ladder_still_has_a_rung():
    """The unsaturated branch that continues — the flag is the negation of that."""
    v = select_saturated_row(sweep((1, 10.0), (16, 30.0)), band=0.5)
    assert not v.saturated
    assert v.continue_at == 32
    assert v.hard_stop_reached is False


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


def test_the_smallest_positive_band_is_accepted():
    """The other side of the zero boundary. Anything above zero is a band.

    The band is derived from the null replicates rather than typed, so its magnitude
    is not this rule's business — only that it is a real interval. A denormal is the
    smallest thing that is.
    """
    v = select_saturated_row(
        sweep((1, 10.0), (4, 12.0)), band=math.nextafter(0.0, math.inf)
    )
    assert not v.saturated  # a 2 dB gain is outside any band this small


def test_a_nan_band_is_refused_rather_than_silently_accepted():
    """Why the guard is written `not band > 0.0` and not `band <= 0.0`.

    The two read identically until the band arrives as a NaN — which is what an
    arithmetic accident upstream produces — and then the second lets it through, and
    every comparison downstream silently answers False. The rule would report an
    unsaturated curve for a reason that has nothing to do with the curve.
    """
    with pytest.raises(ValueError, match="band"):
        select_saturated_row(sweep((1, 10.0), (4, 12.0)), band=float("nan"))


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
