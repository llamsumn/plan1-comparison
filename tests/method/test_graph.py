"""Guard tests for arap_core.graph — what `build_graph` refuses, and why.

`build_graph` is the seam: geometry and an *injected* weighting go in, a validated
`Graph` comes out. Everything it accepts is downstream of four validators and one
invariant assertion, and until this module none of them had a test. That is the
gap worth closing rather than a formality — a validator with no test is a
validator that can be deleted by accident and leave the suite green, and the
failure it was written to catch then arrives later, in a solve, as a linear
algebra error naming nothing.

Each test asserts the exception **type** and enough of the message to identify
*which* guard fired. Matching on the type alone would pass if any other guard in
the same function raised first, which is precisely the confusion these tests are
supposed to remove.

The weighting guards are driven by injecting a deliberately bad `weight_fn`. That
is not a contrivance: the whole design of the seam is that the weighting is a
caller's function, so a caller's function returning the wrong shape, a NaN, or a
negative weight is the realistic failure and the reason the validator is there.
"""

import re

import numpy as np
import pytest

from arap_core.graph import (
    _assert_laplacian_invariants,
    assemble_laplacian,
    build_graph,
    make_rbf_weight_fn,
    rbf_weights,
)

#: A four-vertex path. Small enough to write the failing input by hand, connected
#: enough to be a legal graph, which is what makes it a clean control: every
#: refusal below is caused by the one thing the test perturbs.
POSITIONS = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]
)
EDGES = np.array([[0, 1], [1, 2], [2, 3]])

UNIT = make_rbf_weight_fn(gamma=1.0)


def constant_weight_fn(value):
    """A weight_fn returning `value` for every edge, whatever `value` is."""

    def weight_fn(positions, edges):
        return np.full(edges.shape[0], value, dtype=np.float64)

    return weight_fn


# ── the happy path, so the refusals below are refusals of something ──────────
def test_a_legal_graph_is_accepted():
    """The control. Without it every test in this module could pass vacuously —
    a `build_graph` that rejected everything would satisfy all of them."""
    graph = build_graph(POSITIONS, EDGES, UNIT)

    assert graph.positions.shape == (4, 3)
    assert graph.edges.shape == (3, 2)
    assert graph.weights.shape == (3,)
    assert np.all(graph.weights > 0.0)


# ── rbf_weights' own guard ──────────────────────────────────────────────────
@pytest.mark.parametrize("gamma", [0.0, -1.0, np.nan, np.inf])
def test_rbf_weights_refuses_a_gamma_that_is_not_a_decay_rate(gamma):
    """gamma sets how fast influence decays with distance, so it has to be a
    positive finite number. Zero makes every weight 1 and the falloff vanishes;
    negative makes distant vertices matter *more*; NaN propagates silently into
    the Laplacian and comes back as an unhelpful solver failure."""
    with pytest.raises(ValueError, match="gamma must be finite and > 0"):
        rbf_weights(POSITIONS, EDGES, gamma=gamma)


# ── _validate_positions ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "positions",
    [
        np.zeros((4, 2)),
        np.zeros((4, 4)),
        np.zeros(4),
        np.zeros((2, 4, 3)),
    ],
    ids=["too-few-columns", "too-many-columns", "one-dimensional", "three-dimensional"],
)
def test_positions_that_are_not_n_by_3_are_refused(positions):
    with pytest.raises(ValueError, match=re.escape("positions must be (N, 3)")):
        build_graph(positions, EDGES, UNIT)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_positions_carrying_a_non_finite_value_are_refused(bad):
    """One NaN coordinate is enough. It reaches the weights, then the Laplacian,
    then the factorisation, and the error it eventually causes names none of
    those — so it is caught at the boundary instead."""
    positions = POSITIONS.copy()
    positions[2, 1] = bad
    with pytest.raises(ValueError, match="positions contains non-finite values"):
        build_graph(positions, EDGES, UNIT)


# ── _validate_edges ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "edges",
    [np.zeros((3, 3), dtype=np.int64), np.zeros(6, dtype=np.int64)],
    ids=["three-columns", "flat"],
)
def test_an_edge_list_that_is_not_e_by_2_is_refused(edges):
    with pytest.raises(ValueError, match=re.escape("edges must be (E, 2)")):
        build_graph(POSITIONS, edges, UNIT)


def test_an_empty_edge_list_is_refused():
    """Zero edges is a graph of isolated points: the Laplacian is all zeros, the
    factorisation is singular, and nothing propagates from the handles. Refusing
    it here is what turns that into a sentence rather than a solver crash."""
    with pytest.raises(ValueError, match="edges is empty"):
        build_graph(POSITIONS, np.zeros((0, 2), dtype=np.int64), UNIT)


@pytest.mark.parametrize(
    "edges",
    [np.array([[0, 1], [1, 9]]), np.array([[0, 1], [-1, 2]])],
    ids=["above-range", "below-range"],
)
def test_an_edge_index_outside_the_vertex_range_is_refused(edges):
    with pytest.raises(ValueError, match="edge index out of range for N=4"):
        build_graph(POSITIONS, edges, UNIT)


def test_a_self_loop_is_refused():
    """A self-loop contributes w to a diagonal and −w to the same diagonal, so it
    is invisible in the assembled Laplacian — the graph silently is not the graph
    that was asked for."""
    with pytest.raises(ValueError, match=re.escape("self-loops present (i == j)")):
        build_graph(POSITIONS, np.array([[0, 1], [2, 2]]), UNIT)


def test_an_unsorted_edge_is_refused():
    """`i < j` is what makes the de-duplication check below meaningful: without a
    canonical ordering, (1, 2) and (2, 1) are two rows describing one edge and the
    duplicate detector cannot see it."""
    with pytest.raises(ValueError, match="edges must satisfy i < j"):
        build_graph(POSITIONS, np.array([[0, 1], [2, 1]]), UNIT)


def test_a_repeated_edge_is_refused():
    """A duplicate is not harmless: `tocsr()` sums duplicate entries, so the edge
    would silently carry twice its weight."""
    with pytest.raises(ValueError, match="duplicate edges present"):
        build_graph(POSITIONS, np.array([[0, 1], [1, 2], [0, 1]]), UNIT)


# ── _validate_weights (driven through an injected weight_fn) ────────────────
def test_a_weight_fn_returning_the_wrong_number_of_weights_is_refused():
    """The seam hands the weighting to the caller, so this is the caller's most
    likely mistake: a weight per *vertex* rather than per edge."""

    def one_per_vertex(positions, edges):
        return np.ones(positions.shape[0])

    with pytest.raises(ValueError, match=re.escape("weights must be (3,)")):
        build_graph(POSITIONS, EDGES, one_per_vertex)


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_a_weight_fn_returning_a_non_finite_weight_is_refused(bad):
    with pytest.raises(ValueError, match="weights contains non-finite values"):
        build_graph(POSITIONS, EDGES, constant_weight_fn(bad))


def test_a_weight_fn_returning_a_negative_weight_is_refused():
    """Non-negativity is what makes the Laplacian PSD, and PSD is what makes the
    global step's factorisation valid. A negative weight does not fail loudly —
    it produces an indefinite system that still factors and still returns
    positions, which are simply wrong."""
    with pytest.raises(ValueError, match="weights must be non-negative"):
        build_graph(POSITIONS, EDGES, constant_weight_fn(-1.0))


def test_a_zero_weight_is_allowed():
    """The boundary the guard above must *not* catch. Zero is a legal weight — it
    is how a region is decoupled — and the refusal is of negatives only."""
    graph = build_graph(POSITIONS, EDGES, constant_weight_fn(0.0))
    assert np.array_equal(graph.weights, np.zeros(3))


# ── _assert_laplacian_invariants ────────────────────────────────────────────
# These two cannot be reached through `build_graph`, because `assemble_laplacian`
# is what builds the matrix and it is symmetric with zero row-sums by
# construction. They are driven directly, on hand-built matrices, for the reason
# the assertion exists: it is a check on *assembly*, and it is the thing that
# would catch a future change to assembly getting it wrong. A guard that is only
# ever fed correct input has never been shown to fire at all.
def test_an_asymmetric_laplacian_is_caught():
    L = assemble_laplacian(4, EDGES, np.ones(3)).tolil()
    L[0, 1] = -5.0
    with pytest.raises(AssertionError, match="Laplacian not symmetric"):
        _assert_laplacian_invariants(L.tocsr())


def test_a_laplacian_whose_rows_do_not_sum_to_zero_is_caught():
    """Symmetric but not a Laplacian: adding the same value to two off-diagonal
    positions keeps `L == L.T` and breaks `L @ 1 == 0`. Written this way so the
    second guard is shown firing on its own rather than behind the first."""
    L = assemble_laplacian(4, EDGES, np.ones(3)).tolil()
    L[0, 3] = -1.0
    L[3, 0] = -1.0
    with pytest.raises(AssertionError, match="Laplacian row-sums not zero"):
        _assert_laplacian_invariants(L.tocsr())
