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
