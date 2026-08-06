"""
select.py — anchor (handle) selection helpers.

The driver must specify *the edit*: which Gaussians are handles and where
they go.  In the full pipeline an upstream box predicts this; for now, select
geometrically.

ARAP needs **enough constraint to remove the rigid-body null space** — if
every anchor moves by the same vector you just translate the object; if none
are fixed the system is singular.  ``make_anchors`` therefore warns when no
fixed region is given (the penguin: fix the base/feet, move a wing/head).

Public API
----------
select_box(xyz, lo, hi) -> (idx,)
select_radius(xyz, centre, r) -> (idx,)
make_anchors(xyz, moving_idx, displacement, *, fixed_idx=None) -> Anchors
"""

from __future__ import annotations

import warnings

import numpy as np

from .types import Anchors


def select_box(xyz: np.ndarray, lo, hi) -> np.ndarray:
    """Indices of points inside the axis-aligned box ``[lo, hi]`` (inclusive)."""
    lo = np.asarray(lo, dtype=np.float64)
    hi = np.asarray(hi, dtype=np.float64)
    if lo.shape != (3,) or hi.shape != (3,):
        raise ValueError(f"lo/hi must be 3-vectors, got {lo.shape}, {hi.shape}")
    if np.any(lo > hi):
        raise ValueError(f"box is empty: lo {lo} > hi {hi} in some axis")
    mask = np.all((xyz >= lo) & (xyz <= hi), axis=1)
    return np.where(mask)[0]


def select_radius(xyz: np.ndarray, centre, r: float) -> np.ndarray:
    """Indices of points within radius ``r`` of ``centre``."""
    centre = np.asarray(centre, dtype=np.float64)
    if centre.shape != (3,):
        raise ValueError(f"centre must be a 3-vector, got {centre.shape}")
    if r <= 0:
        raise ValueError(f"radius must be > 0, got {r}")
    dists = np.linalg.norm(xyz - centre, axis=1)
    return np.where(dists <= r)[0]


def make_anchors(
    xyz: np.ndarray,
    moving_idx: np.ndarray,
    displacement,
    *,
    fixed_idx: np.ndarray | None = None,
) -> Anchors:
    """Build an :class:`Anchors` from a moving set and an optional fixed set.

    Parameters
    ----------
    xyz : (N, 3) float64
        Rest positions.
    moving_idx : (M,) int
        Handles that move: ``targets = xyz[moving_idx] + displacement``.
    displacement : (3,) or (M, 3) float64
        Applied to every moving handle (broadcast) or per-handle.
    fixed_idx : (F,) int, optional
        Handles pinned in place: ``targets = xyz[fixed_idx]``.

    Warns
    -----
    UserWarning
        If no fixed region is given — the solve is then translation-ambiguous
        (rigid-body null space not removed) unless the displacement itself
        varies across handles.
    """
    N = xyz.shape[0]
    moving_idx = np.asarray(moving_idx, dtype=np.int64)
    fixed_idx = (
        np.asarray(fixed_idx, dtype=np.int64)
        if fixed_idx is not None
        else np.empty(0, dtype=np.int64)
    )

    if moving_idx.size == 0:
        warnings.warn("moving_idx is empty — no edit is being applied.",
                      stacklevel=2)

    for name, idx in (("moving_idx", moving_idx), ("fixed_idx", fixed_idx)):
        if idx.size and (idx.min() < 0 or idx.max() >= N):
            raise ValueError(f"{name} out of range [0, {N})")
        if len(np.unique(idx)) != len(idx):
            raise ValueError(f"{name} contains duplicate indices")

    overlap = np.intersect1d(moving_idx, fixed_idx)
    if overlap.size:
        raise ValueError(
            f"{overlap.size} indices are in both moving and fixed sets "
            f"(e.g. {overlap[:5]}) — a handle cannot both move and stay"
        )

    if fixed_idx.size == 0:
        warnings.warn(
            "No fixed region given — every anchor moves, so the rigid-body "
            "null space is not removed and the deformation is a translation "
            "(or the system is ill-posed). Pin a region with fixed_idx.",
            stacklevel=2,
        )

    displacement = np.asarray(displacement, dtype=np.float64)
    moving_targets = xyz[moving_idx] + displacement    # broadcasts (3,) or (M,3)

    indices = np.concatenate([moving_idx, fixed_idx])
    targets = np.concatenate([moving_targets, xyz[fixed_idx]])
    return Anchors(indices=indices, targets=targets)
