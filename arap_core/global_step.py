"""
global_step.py — prefactored Poisson position solve for the ARAP global phase.

Fix all per-vertex rotations, solve for deformed positions by back-substituting
into a pre-factored constrained Laplacian.  Split into a one-time factorisation
(``prefactor``) and a per-iteration back-substitution (``solve_positions``) —
re-factoring inside the loop is the canonical ARAP performance bug.

Two constraint styles behind one interface:
- **hard**  — anchored rows replaced with identity → exact handles
- **soft**  — λ added to anchor diagonals → least-squares pull

Public API
----------
prefactor(graph, anchors, *, constraint, penalty) -> Solver
solve_positions(solver, graph, rotations, anchors) -> (N, 3)

Pure NumPy / SciPy, CPU, float64.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import factorized

from .types import Anchors, Graph, Solver


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def prefactor(
    graph: Graph,
    anchors: Anchors,
    *,
    constraint: str = "hard",
    penalty: float = 1e6,
) -> Solver:
    """Factor the constrained Laplacian once, return an opaque Solver.

    Parameters
    ----------
    graph : Graph
    anchors : Anchors
    constraint : {"hard", "soft"}
        "hard" replaces anchored rows with identity (exact handles).
        "soft" adds ``penalty`` to anchor diagonals (least-squares pull).
    penalty : float
        Weight for soft constraints.  Ignored when ``constraint="hard"``.

    Returns
    -------
    Solver
        Call ``solver.solve(b)`` for per-iteration back-substitution.
    """
    _validate_anchors(anchors, graph.n_vertices)
    if constraint not in ("hard", "soft"):
        raise ValueError(f"constraint must be 'hard' or 'soft', got {constraint!r}")

    L = graph.laplacian.tolil()

    if constraint == "hard":
        for idx in anchors.indices:
            L[idx, :] = 0.0
            L[idx, idx] = 1.0
    else:
        if not np.isfinite(penalty) or penalty <= 0:
            raise ValueError(f"penalty must be finite and > 0, got {penalty!r}")
        for idx in anchors.indices:
            L[idx, idx] += penalty

    solve_fn = factorized(L.tocsc())
    return Solver(_solve_fn=solve_fn, constraint=constraint, penalty=penalty)


def solve_positions(
    solver: Solver,
    graph: Graph,
    rotations: np.ndarray,
    anchors: Anchors,
) -> np.ndarray:
    """Solve for deformed positions given fixed rotations.

    Parameters
    ----------
    solver : Solver
        From ``prefactor`` (same graph + anchors).
    graph : Graph
    rotations : (N, 3, 3) float64
        Per-vertex rotations from the local step.
    anchors : Anchors

    Returns
    -------
    positions : (N, 3) float64
        Deformed vertex positions.
    """
    b = _assemble_rhs(graph, rotations)

    if solver.constraint == "hard":
        b[anchors.indices] = anchors.targets
    else:
        b[anchors.indices] += solver.penalty * anchors.targets

    return np.column_stack([solver.solve(b[:, c]) for c in range(3)])


# --------------------------------------------------------------------------- #
# RHS assembly
# --------------------------------------------------------------------------- #
def _assemble_rhs(graph: Graph, rotations: np.ndarray) -> np.ndarray:
    """Build the global-step RHS via scatter-add over edges.

    ``b_i = Σ_j w_ij · ½(R_i + R_j) · (p_i − p_j)``

    Mirror of ``_covariance_stack`` in the local step — same scatter-add
    pattern, different payload.
    """
    edges = graph.edges
    w = graph.weights
    rest = graph.positions

    i_idx = edges[:, 0]
    j_idx = edges[:, 1]

    e_rest = rest[i_idx] - rest[j_idx]                            # (E, 3)
    R_avg = (rotations[i_idx] + rotations[j_idx]) * 0.5           # (E, 3, 3)
    rotated = np.einsum("eij,ej->ei", R_avg, e_rest)              # (E, 3)
    contrib = w[:, None] * rotated                                 # (E, 3)

    b = np.zeros((graph.n_vertices, 3), dtype=np.float64)
    np.add.at(b, i_idx, contrib)
    np.add.at(b, j_idx, -contrib)

    return b


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _validate_anchors(anchors: Anchors, N: int) -> None:
    idx = np.asarray(anchors.indices, dtype=np.int64)
    tgt = np.asarray(anchors.targets, dtype=np.float64)

    if idx.ndim != 1:
        raise ValueError(f"anchors.indices must be 1-D, got shape {idx.shape}")
    A = idx.shape[0]
    if A == 0:
        raise ValueError("anchors.indices is empty — need at least one anchor")
    if A >= N:
        raise ValueError(f"too many anchors ({A}) for {N} vertices")
    if tgt.shape != (A, 3):
        raise ValueError(f"anchors.targets must be ({A}, 3), got {tgt.shape}")
    if not np.isfinite(tgt).all():
        raise ValueError("anchors.targets contains non-finite values")
    if idx.min() < 0 or idx.max() >= N:
        raise ValueError(f"anchor index out of range [0, {N}): [{idx.min()}, {idx.max()}]")
    if len(np.unique(idx)) != A:
        raise ValueError("anchors.indices contains duplicates")
