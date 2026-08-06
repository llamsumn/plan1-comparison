"""Tests for box_b.edge_weights — the edge-weight assignment seam.

Faithfulness + behaviour:
  1. ρ ≡ 1 is a byte-exact no-op (PRIMARY — the item-2 contract test 1 analogue)
  2. only same-region interior edges are scaled; boundary edges keep base
  3. the item-2 single-R reduction (R–R ×ρ, R–D / D–D / A-incident untouched)
  4. make_scoped_weight_fn composes with build_graph and keeps the Laplacian valid
  5. higher ρ on a region makes it deform more rigidly (reproduces study behaviour)
"""

import numpy as np

from box_b.edge_weights import scale_interior_edges, make_scoped_weight_fn
from arap_core.graph import build_graph, make_rbf_weight_fn
from arap_core.driver import arap_solve
from arap_core.select import make_anchors


# ── 1. ρ ≡ 1 identity ───────────────────────────────────────────────────────
def test_rho_one_is_byte_exact_noop():
    rng = np.random.default_rng(0)
    edges = np.array([[0, 1], [1, 2], [2, 3], [0, 3]])
    base = rng.uniform(0.1, 2.0, len(edges))
    labels = np.array([0, 1, 1, 0])
    out = scale_interior_edges(base, edges, labels, np.array([1.0, 1.0]))
    assert np.array_equal(out, base)


# ── 2. only same-region interior edges scale ────────────────────────────────
def test_only_interior_edges_scaled():
    # labels: 0,0,1,1 → edges (0,1) interior-0, (2,3) interior-1, (1,2) boundary
    edges = np.array([[0, 1], [1, 2], [2, 3]])
    base = np.array([1.0, 1.0, 1.0])
    labels = np.array([0, 0, 1, 1])
    out = scale_interior_edges(base, edges, labels, np.array([1.0, 5.0]))
    np.testing.assert_array_equal(out, [1.0, 1.0, 5.0])   # only (2,3) ×5


# ── 3. item-2 single-R reduction ────────────────────────────────────────────
def test_item2_single_region_reduction():
    # region 1 == R (stiff), region 0 == D/A (base). R–R ×ρ; R–D, D–D untouched.
    edges = np.array([[0, 1], [1, 2], [2, 3], [3, 4]])
    base = np.array([2.0, 2.0, 2.0, 2.0])
    r_mask = np.array([0, 1, 1, 1, 0])          # R = {1,2,3}
    rho = 3.0
    out = scale_interior_edges(base, edges, r_mask, np.array([1.0, rho]))
    # (0,1) R–D base; (1,2) R–R ×ρ; (2,3) R–R ×ρ; (3,4) R–D base
    np.testing.assert_array_equal(out, [2.0, 6.0, 6.0, 2.0])


# ── 4. composes with build_graph, Laplacian stays valid ─────────────────────
def test_scoped_weight_fn_builds_valid_graph():
    xyz = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
    edges = np.array([[0, 1], [1, 2], [2, 3]])
    labels = np.array([0, 0, 1, 1])
    wf = make_scoped_weight_fn(make_rbf_weight_fn(gamma=1.0), labels, np.array([1.0, 4.0]))
    graph = build_graph(xyz, edges, wf)          # raises if invariants break
    base = make_rbf_weight_fn(gamma=1.0)(xyz, edges)
    expected = base.copy()
    expected[2] *= 4.0                            # (2,3) is the only R–R edge
    np.testing.assert_allclose(graph.weights, expected)


# ── 5. higher ρ → more rigid region (study behaviour) ───────────────────────
def _grid(nx, ny):
    ix, iy = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    xyz = np.stack([ix.ravel(), iy.ravel(), np.zeros(nx * ny)], axis=1).astype(float)
    vid = lambda a, b: a * ny + b
    e = []
    for a in range(nx):
        for b in range(ny):
            if a + 1 < nx:
                e.append((vid(a, b), vid(a + 1, b)))
            if b + 1 < ny:
                e.append((vid(a, b), vid(a, b + 1)))
    return xyz, np.array(e), vid


def test_higher_rho_makes_region_more_rigid():
    nx, ny = 7, 3
    xyz, edges, vid = _grid(nx, ny)
    labels = (np.arange(nx * ny) // ny >= 4).astype(int)   # R = columns ix >= 4
    left = [vid(0, b) for b in range(ny)]
    right = [vid(nx - 1, b) for b in range(ny)]
    anchors = make_anchors(xyz, np.array(right), np.array([0.0, 2.0, 0.0]),
                           fixed_idx=np.array(left))
    base_fn = make_rbf_weight_fn(gamma=1.0)
    rr = (labels[edges[:, 0]] == 1) & (labels[edges[:, 1]] == 1)

    def intra_R_rotation_spread(rho):
        wf = make_scoped_weight_fn(base_fn, labels, np.array([1.0, rho]))
        res = arap_solve(build_graph(xyz, edges, wf), anchors,
                         max_iters=400, tol=1e-8)
        diffs = res.rotations[edges[rr, 0]] - res.rotations[edges[rr, 1]]
        return np.sqrt((diffs ** 2).sum(axis=(1, 2))).sum()

    # A stiff R rotates as a block → adjacent rotations within R converge.
    assert intra_R_rotation_spread(100.0) < intra_R_rotation_spread(1.0)
