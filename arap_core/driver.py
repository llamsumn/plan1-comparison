"""
driver.py — the local/global alternation loop for ARAP deformation.

Orchestrates everything: factor once, then alternate local step (fit rotations)
and global step (solve positions) to convergence.  The energy trace is the
master debugging instrument — a correct implementation is provably
non-increasing.

Public API
----------
arap_solve(graph, anchors, ...) -> ARAPResult
arap_energy(graph, rest_pos, deformed_pos, rotations) -> float

Pure NumPy / SciPy, CPU, float64.
"""

from __future__ import annotations

import numpy as np

from .types import Anchors, ARAPResult, Graph
from .local_step import fit_rotations
from .global_step import prefactor, solve_positions


def arap_solve(
    graph: Graph,
    anchors: Anchors,
    *,
    max_iters: int = 100,
    tol: float = 1e-4,
    init: np.ndarray | None = None,
    constraint: str = "hard",
    penalty: float = 1e6,
) -> ARAPResult:
    """Run the ARAP alternation loop to convergence.

    Parameters
    ----------
    graph : Graph
    anchors : Anchors
    max_iters : int
        Upper bound on iterations.
    tol : float
        Convergence threshold on max vertex displacement ``‖Δp‖_∞``.
    init : (N, 3) float64, optional
        Warm-start positions.  If *None*, uses rest positions with anchors
        set to their targets.
    constraint : {"hard", "soft"}
        Passed through to ``prefactor``.
    penalty : float
        Passed through to ``prefactor`` (soft constraints only).

    Returns
    -------
    ARAPResult
        Converged positions, rotations, iteration count, convergence flag,
        and the per-iteration energy trace (must be monotone non-increasing).
    """
    N = graph.n_vertices

    # 1. Factor once — never re-factor inside the loop.
    solver = prefactor(graph, anchors, constraint=constraint, penalty=penalty)

    # 2. Initialise positions.
    if init is not None:
        pos = np.array(init, dtype=np.float64)
    else:
        pos = graph.positions.copy()
        pos[anchors.indices] = anchors.targets

    # 3. Alternate local → global.
    energy_trace = []
    rotations = np.tile(np.eye(3, dtype=np.float64), (N, 1, 1))

    for it in range(max_iters):
        rotations = fit_rotations(graph.positions, pos, graph)
        pos_new = solve_positions(solver, graph, rotations, anchors)

        energy = arap_energy(graph, graph.positions, pos_new, rotations)
        energy_trace.append(energy)

        delta = np.linalg.norm(pos_new - pos, axis=1).max()
        pos = pos_new

        if delta < tol:
            return ARAPResult(
                positions=pos,
                rotations=rotations,
                n_iters=it + 1,
                converged=True,
                energy_trace=np.array(energy_trace),
            )

    return ARAPResult(
        positions=pos,
        rotations=rotations,
        n_iters=max_iters,
        converged=False,
        energy_trace=np.array(energy_trace),
    )


def arap_energy(
    graph: Graph,
    rest_pos: np.ndarray,
    deformed_pos: np.ndarray,
    rotations: np.ndarray,
) -> float:
    """Evaluate the ARAP energy directly.

    ``E = Σ_i Σ_{j∈N(i)} w_ij · ‖(p'_i − p'_j) − R_i(p_i − p_j)‖²``

    Used **only** for the convergence trace and the monotonicity test —
    never inside the solve.  Plot ``energy_trace``: any bug surfaces as
    non-monotonicity.

    Parameters
    ----------
    graph : Graph
    rest_pos : (N, 3) float64
    deformed_pos : (N, 3) float64
    rotations : (N, 3, 3) float64

    Returns
    -------
    float
        Total ARAP energy (non-negative).
    """
    edges = graph.edges
    w = graph.weights

    i_idx = edges[:, 0]
    j_idx = edges[:, 1]

    e_rest = rest_pos[i_idx] - rest_pos[j_idx]           # (E, 3)
    e_def = deformed_pos[i_idx] - deformed_pos[j_idx]     # (E, 3)

    # R_i @ e_ij  and  R_j @ e_ij  for each edge
    Re_i = np.einsum("eij,ej->ei", rotations[i_idx], e_rest)   # (E, 3)
    Re_j = np.einsum("eij,ej->ei", rotations[j_idx], e_rest)   # (E, 3)

    # Edge (i,j) appears in vertex i's sum and vertex j's sum
    diff_i = e_def - Re_i
    diff_j = e_def - Re_j

    sq_i = np.einsum("ej,ej->e", diff_i, diff_i)   # (E,)
    sq_j = np.einsum("ej,ej->e", diff_j, diff_j)   # (E,)

    return float(np.sum(w * (sq_i + sq_j)))
