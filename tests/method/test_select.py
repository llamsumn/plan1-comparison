"""Contract tests for arap_core.select (blueprint A.3)."""

import numpy as np
import pytest

from arap_core.select import select_box, select_radius, make_anchors
from arap_core.types import Anchors


@pytest.fixture
def lattice():
    """5x5x5 unit lattice on [0,4]^3 — membership is enumerable by hand."""
    s = np.arange(5, dtype=np.float64)
    return np.array(np.meshgrid(s, s, s, indexing="ij")).reshape(3, -1).T


# ── select_box ──────────────────────────────────────────────────────────────
def test_box_membership(lattice):
    idx = select_box(lattice, lo=[0, 0, 0], hi=[1, 1, 1])
    assert len(idx) == 8                       # 2x2x2 corner block
    assert np.all(lattice[idx] <= 1.0)

    idx_all = select_box(lattice, lo=[0, 0, 0], hi=[4, 4, 4])
    assert len(idx_all) == 125                 # whole lattice

    idx_none = select_box(lattice, lo=[10, 10, 10], hi=[11, 11, 11])
    assert len(idx_none) == 0


def test_box_invalid(lattice):
    with pytest.raises(ValueError, match="empty"):
        select_box(lattice, lo=[1, 0, 0], hi=[0, 4, 4])


# ── select_radius ───────────────────────────────────────────────────────────
def test_radius_membership(lattice):
    idx = select_radius(lattice, centre=[2, 2, 2], r=1.0)
    assert len(idx) == 7                       # centre + 6 axis neighbours
    with pytest.raises(ValueError, match="radius"):
        select_radius(lattice, centre=[2, 2, 2], r=0.0)


# ── make_anchors ────────────────────────────────────────────────────────────
def test_make_anchors_valid(lattice):
    moving = select_box(lattice, [4, 0, 0], [4, 4, 4])   # x=4 face
    fixed = select_box(lattice, [0, 0, 0], [0, 4, 4])    # x=0 face
    disp = np.array([0.5, 0.0, 0.0])

    anchors = make_anchors(lattice, moving, disp, fixed_idx=fixed)

    assert isinstance(anchors, Anchors)
    assert len(anchors.indices) == len(moving) + len(fixed)
    assert len(np.unique(anchors.indices)) == len(anchors.indices)
    np.testing.assert_allclose(anchors.targets[: len(moving)],
                               lattice[moving] + disp)
    np.testing.assert_allclose(anchors.targets[len(moving):], lattice[fixed])


def test_no_fixed_region_warns(lattice):
    moving = select_box(lattice, [4, 0, 0], [4, 4, 4])
    with pytest.warns(UserWarning, match="null space"):
        make_anchors(lattice, moving, [0.5, 0, 0])


def test_overlap_raises(lattice):
    idx = select_box(lattice, [0, 0, 0], [4, 4, 4])[:10]
    with pytest.raises(ValueError, match="both moving and fixed"):
        make_anchors(lattice, idx, [0.1, 0, 0], fixed_idx=idx[:5])


def test_out_of_range_raises(lattice):
    with pytest.raises(ValueError, match="out of range"):
        make_anchors(lattice, np.array([200]), [0.1, 0, 0],
                     fixed_idx=np.array([0]))


# ── the remaining refusals ──────────────────────────────────────────────────
# The four guards below had no test. Three are shape refusals on arguments a
# caller writes by hand — `lo`, `hi` and `centre` are the sort of thing typed as
# a literal, and a 2-vector typo would otherwise broadcast against the (N, 3)
# cloud and silently select the wrong region. The fourth is a warning rather than
# an error, and it is the only place in `select.py` where nothing is raised, so
# it is the one a reader is most likely to assume is unreachable.
@pytest.mark.parametrize(
    "lo, hi",
    [([0, 0], [1, 1, 1]), ([0, 0, 0], [1, 1]), ([0, 0, 0, 0], [1, 1, 1, 1])],
    ids=["lo-too-short", "hi-too-short", "both-too-long"],
)
def test_a_box_corner_that_is_not_a_3_vector_is_refused(lattice, lo, hi):
    with pytest.raises(ValueError, match="lo/hi must be 3-vectors"):
        select_box(lattice, lo=lo, hi=hi)


@pytest.mark.parametrize("centre", [[0, 0], [0, 0, 0, 0]], ids=["short", "long"])
def test_a_radius_centre_that_is_not_a_3_vector_is_refused(lattice, centre):
    with pytest.raises(ValueError, match="centre must be a 3-vector"):
        select_radius(lattice, centre=centre, r=1.0)


def test_an_empty_moving_set_warns_that_no_edit_is_happening(lattice):
    """A selection that matched nothing is the quiet failure this warns about:
    the solve runs, converges, and returns the rest pose, because the region the
    caller meant to move was outside the box they typed."""
    fixed = select_box(lattice, [0, 0, 0], [0, 4, 4])
    with pytest.warns(UserWarning, match="no edit is being applied"):
        make_anchors(lattice, np.empty(0, dtype=np.int64), [0.5, 0, 0],
                     fixed_idx=fixed)


@pytest.mark.parametrize("which", ["moving_idx", "fixed_idx"])
def test_a_repeated_handle_index_is_refused(lattice, which):
    """Parametrised over both sets because the guard is written once and applied
    to each in a loop — testing one would leave the loop itself unexercised, and
    the loop is where a future edit could drop a set."""
    repeated = np.array([1, 1])
    other = np.array([20, 21])
    moving, fixed = (
        (repeated, other) if which == "moving_idx" else (other, repeated)
    )
    with pytest.raises(ValueError, match=f"{which} contains duplicate indices"):
        make_anchors(lattice, moving, [0.1, 0, 0], fixed_idx=fixed)
