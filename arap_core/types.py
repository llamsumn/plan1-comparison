"""
types.py — shared dataclasses / contracts for the ARAP core.

These objects ARE the scope-conditioning interface: the graph weights carry
support/rigidity, anchors carry the handle specification. Both are plain data,
consumed downstream — never hard-coded constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import scipy.sparse as sp


@dataclass
class Graph:
    """A weighted graph over vertices / Gaussian centres.

    Attributes
    ----------
    positions : (N, 3) float64   rest positions
    edges     : (E, 2) int64     undirected edge list, i < j, de-duplicated
    weights   : (E,) float64     per-edge w_ij >= 0
    laplacian : (N, N) csr       symmetric weighted Laplacian, zero row-sums
    """

    positions: np.ndarray
    edges: np.ndarray
    weights: np.ndarray
    laplacian: sp.csr_matrix

    @property
    def n_vertices(self) -> int:
        return self.positions.shape[0]

    @property
    def n_edges(self) -> int:
        return self.edges.shape[0]


@dataclass
class Anchors:
    """Handle specification: which vertices are pinned and where.

    Attributes
    ----------
    indices : (A,) int64    vertex indices held fixed
    targets : (A, 3) float64  their prescribed deformed positions
    """

    indices: np.ndarray
    targets: np.ndarray


@dataclass
class Solver:
    """Opaque handle wrapping a factorised constrained system.

    Exposes one ``solve(b) -> x`` method so the driver is
    factorisation-agnostic (LU, Cholesky, etc.).
    """

    _solve_fn: Callable[[np.ndarray], np.ndarray]
    constraint: str   # "hard" or "soft"
    penalty: float    # only meaningful for constraint="soft"

    def solve(self, b: np.ndarray) -> np.ndarray:
        return self._solve_fn(b)


@dataclass
class ARAPResult:
    """Output of the ARAP alternation loop.

    Attributes
    ----------
    positions    : (N, 3) float64      converged deformed positions
    rotations    : (N, 3, 3) float64   converged per-vertex proper rotations
    n_iters      : int                 iterations run
    converged    : bool                whether tol was reached before max_iters
    energy_trace : (n_iters,) float64  ARAP energy per iteration (must be non-increasing)
    """

    positions: np.ndarray
    rotations: np.ndarray
    n_iters: int
    converged: bool
    energy_trace: np.ndarray
