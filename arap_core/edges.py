"""
edges.py — graph construction from a raw Gaussian cloud.

The core's ``build_graph`` needs an ``edges`` array; a raw ``.ply`` has none.
Build one from k-nearest-neighbours over the Gaussian centres.

⚠️  **`k` here is NOT the K from the weight sweep.**  The K-sweep showed
neighbour count is inert *for ARAP weighting on an existing graph* (γ
dominates).  Here ``k`` controls graph **connectivity itself** — too small
disconnects the cloud into islands that cannot propagate a deformation; too
large bridges gaps that should not be rigid.  Different knob, different
failure mode.  Never conflate the two.

Public API
----------
knn_edges(positions, k, *, symmetric=True) -> (E, 2) int64
assert_connected(N, edges) -> int          (warns loudly if > 1 component)
suggest_k(positions, k_min=6, k_max=20) -> int
"""

from __future__ import annotations

import warnings

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def knn_edges(
    positions: np.ndarray,
    k: int,
    *,
    symmetric: bool = True,
) -> np.ndarray:
    """Build an undirected edge list from k-nearest-neighbours.

    Parameters
    ----------
    positions : (N, 3) float64
        Gaussian centres (or any point cloud).
    k : int
        Neighbours per node.  Connectivity knob — see module docstring.
    symmetric : bool
        *True* (default): keep an edge if **either** endpoint lists the other
        among its k nearest (union — the standard symmetrisation).
        *False*: keep an edge only if **both** endpoints list each other
        (mutual kNN — sparser, drops asymmetric long-range links).

    Returns
    -------
    (E, 2) int64
        Undirected, ``i < j``, de-duplicated, no self-loops — exactly the
        format ``build_graph`` validates.
    """
    positions = np.asarray(positions, dtype=np.float64)
    N = positions.shape[0]

    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if k >= N:
        raise ValueError(f"k={k} must be < number of points ({N})")

    tree = cKDTree(positions)
    _, idx = tree.query(positions, k=k + 1)          # (N, k+1), includes self

    rows = np.repeat(np.arange(N), k + 1)
    cols = idx.ravel()
    keep = rows != cols                               # drop self-matches
    pairs = np.column_stack([rows[keep], cols[keep]])   # directed (i -> j)

    if not symmetric:
        # Mutual kNN: keep (i, j) only if (j, i) is also a directed pair.
        codes = pairs[:, 0] * N + pairs[:, 1]
        reverse = pairs[:, 1] * N + pairs[:, 0]
        pairs = pairs[np.isin(reverse, codes)]

    canon = np.sort(pairs, axis=1)                     # canonicalise to i < j
    edges = np.unique(canon, axis=0).astype(np.int64)  # de-duplicate
    return edges


def assert_connected(N: int, edges: np.ndarray) -> int:
    """Count connected components; warn loudly if the graph is disconnected.

    A disconnected graph means anchors in one component **cannot move
    Gaussians in another** — the deformation silently ignores whole islands.

    Returns
    -------
    int
        Number of connected components (1 = fully connected).
    """
    adj = sp.coo_matrix(
        (np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(N, N)
    )
    n_comp, _ = connected_components(adj, directed=False)
    if n_comp > 1:
        warnings.warn(
            f"Graph has {n_comp} connected components — anchors in one "
            f"component cannot move Gaussians in another. Increase k "
            f"(see suggest_k).",
            stacklevel=2,
        )
    return n_comp


def suggest_k(
    positions: np.ndarray,
    k_min: int = 6,
    k_max: int = 20,
) -> int:
    """Smallest ``k`` in ``[k_min, k_max]`` giving a single-component graph.

    Cheap safety net for an unfamiliar asset.  Raises if even ``k_max``
    leaves the cloud disconnected (the asset has genuinely separate islands
    — bridge them deliberately, not by cranking k).
    """
    N = len(positions)
    for k in range(k_min, k_max + 1):
        edges = knn_edges(positions, k)
        adj = sp.coo_matrix(
            (np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(N, N)
        )
        n_comp, _ = connected_components(adj, directed=False)
        if n_comp == 1:
            return k
    raise ValueError(
        f"Graph still disconnected at k={k_max} — the cloud has genuinely "
        f"separate islands; raising k further would bridge gaps that should "
        f"not be rigid."
    )
