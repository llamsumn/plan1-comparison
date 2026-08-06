"""Contract tests for arap_core.edges (blueprint A.2).

Four checks:
1. Format — output satisfies i<j, unique, no self-loops on a random cloud.
2. Symmetry — a directed pair and its reverse canonicalise to one edge.
3. Connectivity — a two-blob cloud reports 2 components at small k, 1 at
   large k; suggest_k finds the bridge point.
4. Feeds core — knn_edges output passes straight into build_graph without
   tripping its validators.
"""

import numpy as np
import pytest

from arap_core.edges import knn_edges, assert_connected, suggest_k
from arap_core.graph import build_graph, make_rbf_weight_fn


@pytest.fixture
def random_cloud():
    rng = np.random.default_rng(7)
    return rng.uniform(-1, 1, (200, 3))


@pytest.fixture
def two_blobs():
    """Two well-separated 15-point clusters."""
    rng = np.random.default_rng(3)
    blob_a = rng.normal(0.0, 0.1, (15, 3))
    blob_b = rng.normal(0.0, 0.1, (15, 3)) + np.array([10.0, 0.0, 0.0])
    return np.vstack([blob_a, blob_b])


# ── 1. Format ───────────────────────────────────────────────────────────────
def test_format(random_cloud):
    edges = knn_edges(random_cloud, k=8)

    assert edges.dtype == np.int64
    assert edges.ndim == 2 and edges.shape[1] == 2
    assert np.all(edges[:, 0] < edges[:, 1]), "not canonicalised to i<j"
    assert len(np.unique(edges, axis=0)) == len(edges), "duplicate edges"
    assert np.all(edges >= 0) and np.all(edges < len(random_cloud))


def test_k_bounds(random_cloud):
    with pytest.raises(ValueError):
        knn_edges(random_cloud, k=0)
    with pytest.raises(ValueError):
        knn_edges(random_cloud, k=len(random_cloud))


# ── 2. Symmetry ─────────────────────────────────────────────────────────────
def test_symmetric_union_covers_all_neighbours(random_cloud):
    """Union mode: every point's k nearest are all represented as edges."""
    from scipy.spatial import cKDTree

    k = 5
    edges = knn_edges(random_cloud, k=k, symmetric=True)
    edge_set = {tuple(e) for e in edges}

    _, idx = cKDTree(random_cloud).query(random_cloud, k=k + 1)
    for i in range(len(random_cloud)):
        for j in idx[i]:
            if i == j:
                continue
            assert (min(i, j), max(i, j)) in edge_set


def test_mutual_is_subset_of_union(random_cloud):
    union = {tuple(e) for e in knn_edges(random_cloud, k=5, symmetric=True)}
    mutual = {tuple(e) for e in knn_edges(random_cloud, k=5, symmetric=False)}
    assert mutual <= union
    assert len(mutual) < len(union)   # asymmetric links exist in a random cloud


# ── 3. Connectivity ─────────────────────────────────────────────────────────
def test_two_blobs_disconnected_then_bridged(two_blobs):
    N = len(two_blobs)

    edges_small = knn_edges(two_blobs, k=3)
    with pytest.warns(UserWarning, match="2 connected components"):
        n_comp = assert_connected(N, edges_small)
    assert n_comp == 2

    # k >= blob size forces cross-blob neighbours
    edges_large = knn_edges(two_blobs, k=20)
    assert assert_connected(N, edges_large) == 1


def test_suggest_k(two_blobs):
    k = suggest_k(two_blobs, k_min=3, k_max=25)
    assert 15 <= k <= 25   # must reach past the blob size to bridge

    with pytest.raises(ValueError, match="disconnected"):
        suggest_k(two_blobs, k_min=3, k_max=10)


# ── 4. Feeds the core ───────────────────────────────────────────────────────
def test_feeds_build_graph(random_cloud):
    edges = knn_edges(random_cloud, k=8)
    graph = build_graph(random_cloud, edges, make_rbf_weight_fn(gamma=10.0))

    assert graph.n_vertices == len(random_cloud)
    assert graph.n_edges == len(edges)
    assert np.all(graph.weights > 0)
