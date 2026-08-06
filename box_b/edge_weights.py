"""
edge_weights.py — the edge-weight assignment seam (box B → C).

Box B's rigidity field reaches the solver as *scaled edge weights*: given a base
per-edge weighting and a rigidity **segmentation** (per-vertex region labels + a
ρ per region), each region's **interior** edges are multiplied by its ρ. This is
how (mode, magnitude) becomes the edge-weight assignment ``arap_core`` consumes.

The rule is the item-2 mask study's, generalised — an edge ``(i, j)`` is scaled
by ``ρ_r`` iff **both** endpoints lie in the same region ``r``; edges crossing a
region boundary keep their base weight. In the study's single-region case this
is exactly the "R–R interior only" rule (``mask.py``); here every region carries
its own ρ, so soft-hinge (ρ < 1) and stiff-block (ρ > 1) regions coexist.

Two invariants matter and are tested:

* **ρ ≡ 1 is a byte-exact no-op** — a region with ρ = 1 leaves its edges
  untouched, so an all-ones assignment reproduces the base weighting exactly.
* **Base-agnostic** — this composes with *any* ``build_graph`` weight_fn (RBF,
  cotangent, …); it never assumes the study's normalised-RBF base. The core is
  untouched: box B's output drives C purely as data.

Pure NumPy, CPU, float64.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

WeightFn = Callable[[np.ndarray, np.ndarray], np.ndarray]


def scale_interior_edges(
    base_weights: np.ndarray,
    edges: np.ndarray,
    region_of_vertex: np.ndarray,
    rho_of_region: np.ndarray,
) -> np.ndarray:
    """Scale each region's interior edges by its ρ (the R–R-interior rule).

    Parameters
    ----------
    base_weights : (E,) float64
        Base per-edge weights (as produced by a ``build_graph`` weight_fn).
    edges : (E, 2) int
        Undirected edge list (``i < j``, de-duplicated).
    region_of_vertex : (N,) int
        Per-vertex region label; labels index into ``rho_of_region``.
    rho_of_region : (n_regions,) float64
        ρ per region label (> 0). "Deform"/base regions carry ρ = 1.

    Returns
    -------
    (E,) float64
        Scaled weights. Edge ``(i, j)`` is multiplied by ``ρ_{r}`` iff
        ``region(i) == region(j) == r``; boundary-crossing edges keep base
        weight. ``rho_of_region ≡ 1`` returns ``base_weights`` byte-for-byte.

    Notes
    -----
    Scaling is a strictly-positive multiply, so non-negativity and finiteness
    survive — ``build_graph``'s validator and the Laplacian PSD contract hold for
    any ρ > 0.
    """
    w = np.asarray(base_weights, dtype=np.float64)
    edges = np.asarray(edges)
    labels = np.asarray(region_of_vertex)
    rho = np.asarray(rho_of_region, dtype=np.float64)

    if not np.isfinite(rho).all() or np.any(rho <= 0.0):
        raise ValueError("rho_of_region must be finite and > 0")
    if labels.min() < 0 or labels.max() >= rho.shape[0]:
        raise ValueError(
            f"region labels must index rho_of_region [0, {rho.shape[0]}); "
            f"got labels in [{labels.min()}, {labels.max()}]"
        )

    li, lj = labels[edges[:, 0]], labels[edges[:, 1]]
    interior = li == lj                                  # both endpoints same region
    rho_edge = np.where(interior, rho[li], 1.0)          # boundary edges → 1.0
    return w * rho_edge


def make_scoped_weight_fn(
    base_weight_fn: WeightFn,
    region_of_vertex: np.ndarray,
    rho_of_region: np.ndarray,
) -> WeightFn:
    """Wrap a base weight_fn so ``build_graph`` applies the region ρ-scaling.

    The returned callable has the same ``(positions, edges) -> (E,)`` signature
    ``build_graph`` expects: it evaluates the base weighting, then scales each
    region's interior edges by its ρ. This is box B's concrete edge-weight
    assignment — plug it straight into ``build_graph`` in place of the bare base.

    Parameters
    ----------
    base_weight_fn : callable (positions, edges) -> (E,) float64
        Any ``build_graph``-compatible weighting (e.g. ``make_rbf_weight_fn``).
    region_of_vertex : (N,) int
    rho_of_region : (n_regions,) float64

    Returns
    -------
    WeightFn
    """
    labels = np.asarray(region_of_vertex)
    rho = np.asarray(rho_of_region, dtype=np.float64)

    def weight_fn(positions: np.ndarray, edges: np.ndarray) -> np.ndarray:
        base = np.asarray(base_weight_fn(positions, edges), dtype=np.float64)
        return scale_interior_edges(base, edges, labels, rho)

    return weight_fn
