"""
graph.py — weighted graph construction for the scope-conditioned ARAP core.

The graph is the single seam where edit *scope* is decided: the edge weights
w_ij (rigidity / support falloff) and, downstream, which vertices are anchored
are exactly the quantities the scope estimator will eventually predict. Nothing
here is hard-coded — the weight function is *injected*, so a mesh (cotangent
weights) and a Gaussian point graph (RBF weights) traverse the identical code
path with a different `weight_fn`.

Module contents
---------------
build_graph(positions, edges, weight_fn)  -> Graph   # the public entry point
cotangent_weights(positions, edges, faces)-> (E,)    # mesh weight_fn factory input
rbf_weights(positions, edges, gamma)      -> (E,)    # Gaussian-graph weight_fn input
assemble_laplacian(N, edges, weights)     -> csr     # pure L = D - W assembly

All arrays are float64 / int64. Pure NumPy + SciPy, CPU only.
"""

from __future__ import annotations

from functools import partial
from typing import Callable

import numpy as np
import scipy.sparse as sp

from .types import Graph

# A weight function maps (positions, edges) -> per-edge weights of shape (E,).
# Bind any extra parameters (gamma, faces, ...) with functools.partial before
# passing into build_graph, so the call site stays uniform across substrates.
WeightFn = Callable[[np.ndarray, np.ndarray], np.ndarray]


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def build_graph(
    positions: np.ndarray,
    edges: np.ndarray,
    weight_fn: WeightFn,
) -> Graph:
    """Build a fully-populated :class:`Graph` from geometry + an injected weighting.

    Parameters
    ----------
    positions : (N, 3) float64
        Rest vertex / Gaussian-centre positions.
    edges : (E, 2) int
        Undirected edge list. Each row is an index pair (i, j). Assumed
        de-duplicated with i < j (validated below); no self-loops.
    weight_fn : Callable[[positions, edges], (E,) float64]
        Maps geometry + edges to one non-negative weight per edge. Use
        ``functools.partial`` to bind parameters, e.g.::

            wf = partial(rbf_weights, gamma=50.0)
            wf = partial(cotangent_weights, faces=faces)

    Returns
    -------
    Graph
        With ``positions``, ``edges``, ``weights`` and the symmetric weighted
        Laplacian ``laplacian`` populated.

    Contract (enforced)
    -------------------
    * ``positions`` is (N, 3); ``edges`` is (E, 2) with valid indices, i != j,
      i < j, no duplicates.
    * ``weights >= 0`` and finite.
    * ``laplacian`` is symmetric with zero row-sums (``L @ 1 == 0``); it is
      therefore PSD when all weights are non-negative.

    Notes
    -----
    This is the only place the mesh-vs-points distinction is made, and the only
    place neighbour-count vs. weighting trades off — consistent with the
    empirical finding that distance weighting, not K, governs effective support.
    """
    positions = np.asarray(positions, dtype=np.float64)
    edges = np.asarray(edges, dtype=np.int64)

    _validate_positions(positions)
    N = positions.shape[0]
    _validate_edges(edges, N)

    weights = np.asarray(weight_fn(positions, edges), dtype=np.float64)
    _validate_weights(weights, edges.shape[0])

    laplacian = assemble_laplacian(N, edges, weights)
    _assert_laplacian_invariants(laplacian)

    return Graph(
        positions=positions,
        edges=edges,
        weights=weights,
        laplacian=laplacian,
    )


# --------------------------------------------------------------------------- #
# Weight functions (injected into build_graph)
# --------------------------------------------------------------------------- #
def rbf_weights(
    positions: np.ndarray,
    edges: np.ndarray,
    gamma: float,
) -> np.ndarray:
    """Gaussian (RBF) edge weights for a point / Gaussian graph.

        w_ij = exp(-gamma * ||p_i - p_j||^2)

    ``gamma`` is a *scope control*, not a constant: it sets how fast influence
    decays with distance and therefore the effective support extent. Bind it
    with ``partial(rbf_weights, gamma=...)`` before passing to build_graph.

    Parameters
    ----------
    positions : (N, 3) float64
    edges     : (E, 2) int
    gamma     : float > 0
        Decay rate. Larger gamma -> tighter, more local support.

    Returns
    -------
    (E,) float64 in (0, 1], strictly positive.
    """
    if not np.isfinite(gamma) or gamma <= 0.0:
        raise ValueError(f"rbf_weights: gamma must be finite and > 0, got {gamma!r}")

    d = positions[edges[:, 0]] - positions[edges[:, 1]]      # (E, 3)
    sq_dist = np.einsum("ij,ij->i", d, d)                    # (E,) squared length
    return np.exp(-gamma * sq_dist)


def cotangent_weights(
    positions: np.ndarray,
    edges: np.ndarray,
    faces: np.ndarray,
) -> np.ndarray:
    """Cotangent edge weights for a triangle mesh.

        w_ij = 1/2 * (cot(alpha_ij) + cot(beta_ij))

    where alpha, beta are the angles opposite edge (i, j) in the (up to two)
    triangles sharing it. These are the standard discrete-Laplacian weights;
    they make the global step a discrete Poisson solve on the mesh.

    Parameters
    ----------
    positions : (N, 3) float64
    edges     : (E, 2) int   (i < j, de-duplicated)
    faces     : (F, 3) int   triangle vertex indices (CCW)

    Returns
    -------
    (E,) float64, clamped to >= 0.

    Notes
    -----
    Obtuse triangles can yield negative cotangents and hence a negative,
    indefinite Laplacian. We clamp negatives to 0 so L stays PSD — the standard
    pragmatic guard. (Intrinsic-Delaunay reweighting is the principled fix;
    out of scope for the core.)
    """
    faces = np.asarray(faces, dtype=np.int64)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError(f"cotangent_weights: faces must be (F, 3), got {faces.shape}")

    # Accumulate cotangent contributions per undirected vertex pair, then read
    # them off for the requested edge list.
    cot_sum: dict[tuple[int, int], float] = {}

    # For each triangle (a, b, c), the angle at vertex `a` is opposite edge (b, c).
    # Its cotangent contributes to the weight of edge (b, c). Cycle over corners.
    for tri in faces:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        for opp, (u, v) in (
            (a, (b, c)),
            (b, (c, a)),
            (c, (a, b)),
        ):
            cot = _cotangent_at(positions[opp], positions[u], positions[v])
            key = (u, v) if u < v else (v, u)
            cot_sum[key] = cot_sum.get(key, 0.0) + 0.5 * cot

    out = np.empty(edges.shape[0], dtype=np.float64)
    for e, (i, j) in enumerate(edges):
        key = (int(i), int(j)) if i < j else (int(j), int(i))
        out[e] = cot_sum.get(key, 0.0)

    return np.clip(out, 0.0, None)


def _cotangent_at(p_opp: np.ndarray, p_u: np.ndarray, p_v: np.ndarray) -> float:
    """cot of the angle at ``p_opp`` in triangle (p_opp, p_u, p_v).

    cot(theta) = cos / sin = (e1 . e2) / ||e1 x e2||, with e1, e2 the two edges
    emanating from p_opp.
    """
    e1 = p_u - p_opp
    e2 = p_v - p_opp
    cross = np.linalg.norm(np.cross(e1, e2))
    if cross < 1e-12:           # degenerate / collinear triangle
        return 0.0
    return float(np.dot(e1, e2) / cross)


# --------------------------------------------------------------------------- #
# Laplacian assembly (geometry-free: pure L = D - W)
# --------------------------------------------------------------------------- #
def assemble_laplacian(
    N: int,
    edges: np.ndarray,
    weights: np.ndarray,
) -> sp.csr_matrix:
    """Assemble the symmetric weighted graph Laplacian ``L = D - W``.

    Off-diagonal:  L_ij = L_ji = -w_ij  for each edge (i, j).
    Diagonal:      L_ii = sum_j w_ij     (so each row sums to zero).

    Parameters
    ----------
    N       : int          number of vertices
    edges   : (E, 2) int
    weights : (E,) float64

    Returns
    -------
    scipy.sparse.csr_matrix, shape (N, N), symmetric, zero row-sums.

    Notes
    -----
    Pure assembly, no positions involved — deliberately separable so the
    zero-row-sum / symmetry invariants can be unit-tested in isolation from any
    geometry or weighting scheme.
    """
    i = edges[:, 0]
    j = edges[:, 1]

    # Off-diagonal: -w on both (i, j) and (j, i). Diagonal: +w on (i, i), (j, j).
    rows = np.concatenate([i, j, i, j])
    cols = np.concatenate([j, i, i, j])
    data = np.concatenate([-weights, -weights, weights, weights])

    # COO with duplicate (row, col) entries; tocsr() sums duplicates, which is
    # exactly the diagonal accumulation we want.
    L = sp.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()
    L.eliminate_zeros()
    return L


# --------------------------------------------------------------------------- #
# Validators / invariant guards
# --------------------------------------------------------------------------- #
def _validate_positions(positions: np.ndarray) -> None:
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"positions must be (N, 3), got {positions.shape}")
    if not np.isfinite(positions).all():
        raise ValueError("positions contains non-finite values")


def _validate_edges(edges: np.ndarray, N: int) -> None:
    if edges.ndim != 2 or edges.shape[1] != 2:
        raise ValueError(f"edges must be (E, 2), got {edges.shape}")
    if edges.size == 0:
        raise ValueError("edges is empty; the graph would be disconnected")
    if edges.min() < 0 or edges.max() >= N:
        raise ValueError(
            f"edge index out of range for N={N}: "
            f"[{edges.min()}, {edges.max()}]"
        )
    if (edges[:, 0] == edges[:, 1]).any():
        raise ValueError("self-loops present (i == j) in edges")
    if (edges[:, 0] >= edges[:, 1]).any():
        raise ValueError("edges must satisfy i < j (sorted, de-duplicated)")
    # Duplicate detection on the canonical (i<j) ordering.
    view = np.ascontiguousarray(edges).view(
        np.dtype((np.void, edges.dtype.itemsize * 2))
    )
    if np.unique(view).size != edges.shape[0]:
        raise ValueError("duplicate edges present")


def _validate_weights(weights: np.ndarray, E: int) -> None:
    if weights.shape != (E,):
        raise ValueError(f"weights must be ({E},), got {weights.shape}")
    if not np.isfinite(weights).all():
        raise ValueError("weights contains non-finite values")
    if (weights < 0).any():
        raise ValueError("weights must be non-negative (got a negative weight)")


def _assert_laplacian_invariants(L: sp.csr_matrix, tol: float = 1e-9) -> None:
    # Symmetry: ||L - L^T||_inf small.
    asym = abs(L - L.T)
    if asym.nnz and asym.max() > tol:
        raise AssertionError(f"Laplacian not symmetric (max asym {asym.max():.2e})")
    # Zero row-sums: L @ 1 ≈ 0.
    row_sums = np.asarray(L @ np.ones(L.shape[0]))
    if np.abs(row_sums).max() > tol:
        raise AssertionError(
            f"Laplacian row-sums not zero (max |sum| {np.abs(row_sums).max():.2e})"
        )


# --------------------------------------------------------------------------- #
# Convenience: ready-bound weight functions
# --------------------------------------------------------------------------- #
def make_rbf_weight_fn(gamma: float) -> WeightFn:
    """Return an rbf weight_fn with ``gamma`` bound — sugar over functools.partial."""
    return partial(rbf_weights, gamma=gamma)


def make_cotangent_weight_fn(faces: np.ndarray) -> WeightFn:
    """Return a cotangent weight_fn with ``faces`` bound."""
    return partial(cotangent_weights, faces=faces)
