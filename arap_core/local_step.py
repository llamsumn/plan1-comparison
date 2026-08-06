"""
local_step.py — per-vertex rotation fit via SVD for the ARAP local phase.

Fix deformed positions, solve each per-vertex rotation R_i independently by
finding the closest proper rotation (SO(3)) to the weighted covariance of
rest-vs-deformed edge vectors.  This is the 3D lift of the verified 2D toy.

Public API
----------
fit_rotations(rest_pos, deformed_pos, graph) -> (N, 3, 3)

All arrays float64.  Fully vectorised — no Python loop over vertices.
Pure NumPy, CPU only.
"""

from __future__ import annotations

import numpy as np

from .types import Graph


def fit_rotations(
    rest_pos: np.ndarray,
    deformed_pos: np.ndarray,
    graph: Graph,
) -> np.ndarray:
    """Solve the local ARAP step: best-fit proper rotation per vertex.

    Parameters
    ----------
    rest_pos : (N, 3) float64
        Rest (undeformed) vertex positions.
    deformed_pos : (N, 3) float64
        Current deformed vertex positions.
    graph : Graph
        Weighted graph (edges, weights).

    Returns
    -------
    R : (N, 3, 3) float64
        Per-vertex proper rotations.  ``R[i]`` is orthogonal with ``det = +1``.
    """
    S = _covariance_stack(rest_pos, deformed_pos, graph)
    return _project_to_SO3(S)


def _covariance_stack(
    rest_pos: np.ndarray,
    deformed_pos: np.ndarray,
    graph: Graph,
) -> np.ndarray:
    """Build the (N, 3, 3) weighted covariance matrices for all vertices.

    For each vertex i:
        S_i = Σ_{j ∈ N(i)} w_ij · e_ij · e'_ij^T

    where e_ij = p_i − p_j (rest) and e'_ij = p'_i − p'_j (deformed).

    Accumulated via ``np.add.at`` scatter-add over the edge list so there is
    no Python loop over vertices.
    """
    N = graph.n_vertices
    edges = graph.edges          # (E, 2), i < j
    w = graph.weights            # (E,)

    i_idx = edges[:, 0]
    j_idx = edges[:, 1]

    e_rest = rest_pos[i_idx] - rest_pos[j_idx]           # (E, 3)
    e_def = deformed_pos[i_idx] - deformed_pos[j_idx]     # (E, 3)

    # Weighted outer products: w_ij * e_ij ⊗ e'_ij  → (E, 3, 3)
    we_rest = w[:, None] * e_rest                          # (E, 3)
    outer = we_rest[:, :, None] * e_def[:, None, :]        # (E, 3, 3)

    S = np.zeros((N, 3, 3), dtype=np.float64)

    # Edge (i, j) contributes to vertex i with (e_ij, e'_ij)
    np.add.at(S, i_idx, outer)

    # Edge (i, j) also contributes to vertex j with (e_ji, e'_ji) = (−e_ij, −e'_ij)
    # The outer product of negated vectors is the same: (−e)(−e')^T = e e'^T
    np.add.at(S, j_idx, outer)

    return S


def _project_to_SO3(S: np.ndarray) -> np.ndarray:
    """Project each 3×3 matrix to the nearest proper rotation via SVD.

    For each S_i = U Σ V^T, the closest rotation is R_i = V U^T.
    If det(R_i) < 0 (a reflection), negate the column of V corresponding
    to the smallest singular value, then recompute R = V U^T.

    Parameters
    ----------
    S : (N, 3, 3) float64
        Covariance matrices.

    Returns
    -------
    R : (N, 3, 3) float64
        Proper rotations (R^T R = I, det R = +1).
    """
    U, sigma, Vt = np.linalg.svd(S)    # U: (N,3,3), sigma: (N,3), Vt: (N,3,3)
    V = np.swapaxes(Vt, -2, -1)        # (N, 3, 3)

    R = np.einsum("nij,nkj->nik", V, U)  # V @ U^T per vertex

    det = np.linalg.det(R)               # (N,)
    needs_fix = det < 0

    if needs_fix.any():
        min_col = np.argmin(sigma[needs_fix], axis=1)
        V_fix = V[needs_fix].copy()
        V_fix[np.arange(min_col.shape[0]), :, min_col] *= -1
        R[needs_fix] = np.einsum("nij,nkj->nik", V_fix, U[needs_fix])

    # Isolated vertices (zero covariance) get an arbitrary SVD result;
    # default them to identity since there are no edges to constrain them.
    degenerate = sigma.max(axis=1) < 1e-14
    if degenerate.any():
        R[degenerate] = np.eye(3, dtype=np.float64)

    return R
