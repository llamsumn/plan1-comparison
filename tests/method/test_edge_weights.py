"""Tests for box_b.edge_weights — the edge-weight assignment seam.

Faithfulness + behaviour:
  1. ρ ≡ 1 is a byte-exact no-op (PRIMARY — the item-2 contract test 1 analogue)
  2. only same-region interior edges are scaled; boundary edges keep base
  3. the item-2 single-R reduction (R–R ×ρ, R–D / D–D / A-incident untouched)
  4. make_scoped_weight_fn composes with build_graph and keeps the Laplacian valid
  5. higher ρ on a region makes it deform more rigidly (reproduces study behaviour)
  6. the two validation guards, driven at the values they exist to refuse

Section 6 was added after measurement rather than by inspection. This module was
believed to be the strongest in the repository — every mutant killed — and it was
not: the exploratory count included the `sha256` checks, which fail on *any* byte
changing here, because this file's rule is pinned in `evidence/PROVENANCE.toml` and
its hash is printed in the published table's footer. With those excluded, five
mutants survived, all of them in the two guards below, which nothing drove at all:
`ρ ≤ 0` could become `ρ < 0` and a rigidity of exactly zero would have been accepted
as valid. That is the argument for the mutation record, made by the module it was
supposed to exonerate.

Each of the six was watched failing against the wrong implementation before it was
kept. What was driven, and which test caught it:

| the source, made wrong | the test that failed |
|---|---|
| `np.any(rho <= 0.0)` → `rho < 0.0` | `test_a_rigidity_of_exactly_zero_is_refused` |
| `not np.isfinite(rho).all() or …` → `and` | `test_a_non_finite_rigidity_is_refused` |
| `labels.max() >= rho.shape[0]` → `>` | `test_a_label_one_past_the_last_region_is_refused` |
| `labels.min() < 0 or …` → `and` | `test_a_negative_label_is_refused` |
| `rho.shape[0]` in the message → `shape[1]` | `test_a_label_one_past_the_last_region_is_refused` |

With those six in place the module kills all twelve of its mutants — and this time it
is the tests doing it rather than a checksum.
"""

import numpy as np
import pytest

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


# ── 6. the two guards, at the boundary of what each refuses ─────────────────
# `scale_interior_edges` states two preconditions — ρ finite and strictly positive,
# labels indexing `rho_of_region` — and until now nothing drove either. Both are
# boundaries rather than ranges: ρ = 0 is the first refused rigidity, and a label
# equal to the region count is the first refused label. Each is asserted on the
# refused side and on the accepted side, so neither guard can be widened or narrowed
# by one without a test noticing.
EDGES = np.array([[0, 1], [1, 2], [2, 3]])
BASE = np.array([1.0, 1.0, 1.0])
LABELS = np.array([0, 0, 1, 1])


def test_a_rigidity_of_exactly_zero_is_refused():
    """ρ > 0 is the contract, and zero is on the wrong side of it.

    Not pedantry about a value nobody would pass: ρ = 0 zeroes every interior edge
    of its region, which drops those rows out of the Laplacian entirely and leaves
    the solve on a graph that is silently disconnected. The refusal is what keeps
    that from becoming a numerical mystery downstream.
    """
    with pytest.raises(ValueError, match="finite and > 0"):
        scale_interior_edges(BASE, EDGES, LABELS, np.array([1.0, 0.0]))


def test_the_smallest_positive_rigidity_is_accepted():
    """The other side of the same boundary: anything above zero is a rigidity."""
    out = scale_interior_edges(
        BASE, EDGES, LABELS, np.array([1.0, np.nextafter(0.0, 1.0)])
    )
    assert out[0] == 1.0  # the interior edge of region 0, ρ = 1
    assert out[2] > 0.0  # scaled, and still positive


def test_a_non_finite_rigidity_is_refused():
    """Why the guard is two conditions and not one.

    A NaN is not caught by `ρ ≤ 0` — every comparison against NaN is False — so
    without the finiteness half it would pass straight through and turn the whole
    weight vector into NaNs at the multiply. An infinity is the same story from the
    other end. Both are asserted so the two halves cannot be collapsed into one.
    """
    for bad in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="finite and > 0"):
            scale_interior_edges(BASE, EDGES, LABELS, np.array([1.0, bad]))


def test_a_label_one_past_the_last_region_is_refused():
    """Labels index `rho_of_region`, so the region count itself is out of range.

    An off-by-one here does not raise on its own — numpy would index and either wrap
    or fail somewhere further in — so the range check is the only thing standing
    between a mislabelled vertex and a rigidity taken from the wrong region.
    """
    with pytest.raises(ValueError, match="region labels must index"):
        scale_interior_edges(BASE, EDGES, np.array([0, 0, 2, 2]), np.array([1.0, 5.0]))


def test_the_last_valid_label_is_accepted():
    """And the boundary on the legal side: `n_regions - 1` indexes the last ρ."""
    out = scale_interior_edges(
        BASE, EDGES, np.array([0, 0, 2, 2]), np.array([1.0, 1.0, 5.0])
    )
    np.testing.assert_array_equal(out, [1.0, 1.0, 5.0])


def test_a_negative_label_is_refused():
    """The other end of the range, which numpy would otherwise read as an index
    counted from the back — quietly returning the wrong region's ρ rather than
    failing."""
    with pytest.raises(ValueError, match="region labels must index"):
        scale_interior_edges(BASE, EDGES, np.array([0, 0, -1, -1]), np.array([1.0, 5.0]))
