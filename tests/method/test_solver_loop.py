"""The two exits of the alternation loop, and the degenerate-vertex fallback.

`arap_solve` has two ways to return and only one of them was ever taken by a
test. The unconverged exit — the loop running out of iterations — is the one that
matters more for a reader, because it is the one that returns a result that looks
like every other result and is *not* converged. `converged` is a field on the
returned object rather than an exception, so a caller that does not read it gets
a plausible answer from a solve that never settled. These tests pin both exits
and pin the distinction between them.

`fit_rotations`' degenerate branch is the third thing here. A vertex whose edges
all carry zero weight has a zero covariance matrix, and the SVD of a zero matrix
gives an arbitrary orthogonal factor — arbitrary, not identity, and potentially a
reflection. Defaulting to identity is what stops an unconstrained vertex being
handed a rotation nothing asked for.
"""

import numpy as np
import pytest

from arap_core.driver import arap_energy, arap_solve
from arap_core.graph import build_graph, make_rbf_weight_fn
from arap_core.local_step import fit_rotations
from arap_core.types import Anchors

POSITIONS = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]
)
EDGES = np.array([[0, 1], [1, 2], [2, 3]])

#: A bend large enough that the alternation has real work to do — a small
#: displacement converges in one iteration and would not distinguish the exits.
ANCHORS = Anchors(
    indices=np.array([0, 3]),
    targets=np.array([[0.0, 0.0, 0.0], [2.0, 2.0, 0.0]]),
)


@pytest.fixture
def graph():
    return build_graph(POSITIONS, EDGES, make_rbf_weight_fn(gamma=1.0))


def test_the_loop_reports_convergence_when_it_settles(graph):
    result = arap_solve(graph, ANCHORS, max_iters=200, tol=1e-9)

    assert result.converged
    assert result.n_iters < 200
    assert len(result.energy_trace) == result.n_iters


def test_the_loop_reports_non_convergence_when_it_runs_out_of_iterations(graph):
    """The exit that returns a usable-looking result from an unfinished solve.

    `n_iters == max_iters` is the tell, and it is asserted alongside the flag
    because the two together are what a caller reads to tell this apart from a
    solve that happened to converge on its last iteration."""
    result = arap_solve(graph, ANCHORS, max_iters=2, tol=1e-12)

    assert not result.converged
    assert result.n_iters == 2
    assert len(result.energy_trace) == 2
    assert np.all(np.isfinite(result.positions))


def test_an_unconverged_result_still_satisfies_the_hard_constraints(graph):
    """Stopping early loses the interior, not the handles: the anchors are placed
    by the right-hand side on every iteration, so they are exact from the first.
    Worth stating, because it is why an unconverged result is degraded rather
    than meaningless."""
    result = arap_solve(graph, ANCHORS, max_iters=1, tol=1e-12)
    np.testing.assert_allclose(
        result.positions[ANCHORS.indices], ANCHORS.targets, atol=1e-12
    )


def test_the_energy_does_not_rise_along_the_unconverged_trace(graph):
    """The monotonicity property is a property of the alternation, not of
    convergence. If it only held for solves that finished, it would not be
    diagnosing anything."""
    trace = arap_solve(graph, ANCHORS, max_iters=6, tol=1e-12).energy_trace
    rises = np.diff(trace)
    assert np.all(rises <= 1e-9 * max(1.0, abs(trace[0]))), trace


def test_a_warm_start_is_used_rather_than_the_rest_pose(graph):
    """`init` is the other untested branch of the initialisation. Passing the
    converged answer back in should leave it there — one iteration, no movement,
    which is only true if `init` was read at all."""
    converged = arap_solve(graph, ANCHORS, max_iters=200, tol=1e-9)
    restarted = arap_solve(graph, ANCHORS, init=converged.positions, tol=1e-9)

    assert restarted.n_iters == 1
    np.testing.assert_allclose(restarted.positions, converged.positions, atol=1e-6)


# ── the degenerate vertex ───────────────────────────────────────────────────
def test_a_vertex_whose_covariance_is_below_the_noise_floor_gets_the_identity():
    """Weights small enough that the covariance carries no usable information.

    **Exactly zero is the wrong input to test this with, and that is worth
    recording.** `svd` of the zero matrix returns identity factors on every
    implementation seen here, so `R = V Uᵀ` is identity whether or not the
    fallback runs — a test built on zero weights passes with the fallback
    deleted, which makes it a test of NumPy rather than of this code.

    Tiny-but-structured weights are the discriminating case. At 1e-16 the largest
    singular value is below the 1e-14 floor, so the guard fires; without it the
    SVD happily fits the rotation implied by numerical dust, which here differs
    from identity by 0.64 — a two-thirds-of-a-radian rotation conjured out of a
    covariance that means nothing.
    """
    graph = build_graph(
        POSITIONS, EDGES, lambda positions, edges: np.full(edges.shape[0], 1e-16)
    )
    theta = 0.7
    rotation = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta), np.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    rotations = fit_rotations(POSITIONS, POSITIONS @ rotation.T, graph)

    np.testing.assert_array_equal(rotations, np.tile(np.eye(3), (4, 1, 1)))


def test_a_vertex_with_no_edges_at_all_also_gets_the_identity():
    """The zero-weight case, kept as a boundary rather than as the guard's test.

    Zero weights are legal — `build_graph` refuses negatives, not zeros — so this
    is reachable through the public path, and it should behave the same way. It
    simply cannot show the fallback firing, for the reason above."""
    graph = build_graph(
        POSITIONS, EDGES, lambda positions, edges: np.zeros(edges.shape[0])
    )
    deformed = POSITIONS + np.array([0.0, 1.0, 0.0])

    rotations = fit_rotations(POSITIONS, deformed, graph)

    np.testing.assert_array_equal(rotations, np.tile(np.eye(3), (4, 1, 1)))


def test_a_well_conditioned_vertex_is_not_given_the_identity_fallback():
    """The negative control for the test above. Without it, a `fit_rotations`
    that returned identity unconditionally would pass — and that is exactly the
    shape of bug the fallback could hide."""
    graph = build_graph(POSITIONS, EDGES, make_rbf_weight_fn(gamma=1.0))
    theta = 0.4
    rotation = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta), np.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    deformed = POSITIONS @ rotation.T

    rotations = fit_rotations(POSITIONS, deformed, graph)

    assert not np.allclose(rotations[1], np.eye(3))
    np.testing.assert_allclose(rotations[1], rotation, atol=1e-9)


def test_the_energy_of_a_zero_weight_graph_is_zero(graph):
    """`arap_energy` weights every edge term, so a graph with no effective edges
    has no energy however far it is deformed. The companion to the fallback
    above: it says why an isolated vertex is unconstrained rather than
    misbehaving."""
    zero = build_graph(
        POSITIONS, EDGES, lambda positions, edges: np.zeros(edges.shape[0])
    )
    energy = arap_energy(
        zero, POSITIONS, POSITIONS * 5.0, np.tile(np.eye(3), (4, 1, 1))
    )
    assert energy == 0.0
