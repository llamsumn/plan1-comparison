"""Guard and contract tests for arap_core.global_step — anchors, and both
constraint styles.

Two things are covered here that were not covered anywhere.

**The anchor validators.** Seven refusals in `_validate_anchors`, all of them
reached through `prefactor`, which is the public entry point and the only way a
caller meets them. They are uniform in shape — bad anchors in, specific message
out — so they are parametrised, and each case asserts the fragment that names
*which* of the seven fired. Type alone would not: all seven raise `ValueError`
from the same function, so a test matching only the type would pass no matter
which one it actually tripped.

**The soft-constraint path.** `constraint="soft"` is supported and documented and
every call site in this repository passes `"hard"`. That makes it the one branch
of the core that a reader could reasonably suspect of never having run. It has
now run: the tests below drive it through `prefactor` and `solve_positions` and
pin the property that distinguishes it from `"hard"` — anchors are *pulled*
rather than *placed*, and the pull tightens as the penalty grows. Testing it
rather than deleting it is the cheaper of the two: deleting would reach into four
files, change a public signature, and move five pinned digests.
"""

import re

import numpy as np
import pytest

from arap_core.global_step import prefactor, solve_positions
from arap_core.graph import build_graph, make_rbf_weight_fn
from arap_core.types import Anchors

POSITIONS = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]
)
EDGES = np.array([[0, 1], [1, 2], [2, 3]])

#: Vertex 0 pinned where it is, vertex 3 lifted. Two anchors on four vertices
#: leaves two free, which is enough for the interior to have somewhere to go.
TARGETS = np.array([[0.0, 0.0, 0.0], [3.0, 1.0, 0.0]])


@pytest.fixture
def graph():
    return build_graph(POSITIONS, EDGES, make_rbf_weight_fn(gamma=1.0))


@pytest.fixture
def anchors():
    return Anchors(indices=np.array([0, 3]), targets=TARGETS.copy())


@pytest.fixture
def identity_rotations():
    """No rotation anywhere. The global step is a linear solve given fixed
    rotations, so identity is a perfectly ordinary input and it keeps these tests
    about the constraint handling rather than about the local step."""
    return np.tile(np.eye(3), (4, 1, 1))


# ── _validate_anchors, through prefactor ────────────────────────────────────
@pytest.mark.parametrize(
    "indices, targets, expected",
    [
        (
            np.zeros((2, 2), dtype=np.int64),
            np.zeros((2, 3)),
            "anchors.indices must be 1-D",
        ),
        (
            np.empty(0, dtype=np.int64),
            np.zeros((0, 3)),
            "anchors.indices is empty",
        ),
        (
            np.arange(4),
            np.zeros((4, 3)),
            re.escape("too many anchors (4) for 4 vertices"),
        ),
        (
            np.array([0, 3]),
            np.zeros((2, 2)),
            re.escape("anchors.targets must be (2, 3)"),
        ),
        (
            np.array([0, 3]),
            np.array([[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]]),
            "anchors.targets contains non-finite values",
        ),
        (
            np.array([0, 9]),
            np.zeros((2, 3)),
            re.escape("anchor index out of range [0, 4)"),
        ),
        (
            np.array([2, 2]),
            np.zeros((2, 3)),
            "anchors.indices contains duplicates",
        ),
    ],
    ids=[
        "indices-not-1d",
        "no-anchors-at-all",
        "every-vertex-anchored",
        "targets-not-a-by-3",
        "target-is-not-finite",
        "index-past-the-end",
        "the-same-vertex-twice",
    ],
)
def test_prefactor_refuses_anchors_it_cannot_solve_with(
    graph, indices, targets, expected
):
    with pytest.raises(ValueError, match=expected):
        prefactor(graph, Anchors(indices=indices, targets=targets))


def test_anchoring_every_vertex_but_one_is_allowed(graph):
    """The boundary the `too many anchors` guard must not overshoot. `A >= N` is
    refused because it leaves no free vertex to solve for; `A == N - 1` leaves
    exactly one and is a legal, if trivial, system."""
    solver = prefactor(
        graph, Anchors(indices=np.array([0, 1, 2]), targets=np.zeros((3, 3)))
    )
    assert solver.constraint == "hard"


# ── the constraint guard ────────────────────────────────────────────────────
@pytest.mark.parametrize("constraint", ["", "HARD", "penalty", "least-squares"])
def test_prefactor_refuses_a_constraint_style_it_does_not_implement(
    graph, anchors, constraint
):
    """Silently treating an unrecognised style as one of the two would be the bad
    outcome: `"HARD"` falling through to the soft branch gives a solve that runs,
    converges, and quietly does not pin the handles."""
    with pytest.raises(ValueError, match="constraint must be 'hard' or 'soft'"):
        prefactor(graph, anchors, constraint=constraint)


@pytest.mark.parametrize("penalty", [0.0, -1.0, np.nan, np.inf])
def test_a_soft_constraint_refuses_a_penalty_that_is_not_a_pull(
    graph, anchors, penalty
):
    """The penalty is the strength of the pull, so it has to be positive and
    finite. Zero is the interesting one: it leaves the Laplacian singular, and
    the factorisation of a singular matrix is where this would otherwise surface
    — far from the mistake."""
    with pytest.raises(ValueError, match="penalty must be finite and > 0"):
        prefactor(graph, anchors, constraint="soft", penalty=penalty)


def test_the_penalty_is_ignored_when_the_constraint_is_hard(graph, anchors):
    """Documented behaviour, and worth pinning: a hard constraint never reads the
    penalty, so a nonsensical one is not an error there."""
    solver = prefactor(graph, anchors, constraint="hard", penalty=-1.0)
    assert solver.constraint == "hard"


# ── the soft path, end to end ───────────────────────────────────────────────
def test_a_hard_constraint_places_the_anchors_exactly(
    graph, anchors, identity_rotations
):
    """The reference the soft case is read against."""
    positions = solve_positions(
        prefactor(graph, anchors), graph, identity_rotations, anchors
    )
    np.testing.assert_allclose(positions[anchors.indices], TARGETS, atol=1e-12)


def test_a_soft_constraint_pulls_the_anchors_without_placing_them(
    graph, anchors, identity_rotations
):
    """The property that makes "soft" a different thing rather than a slower
    spelling of "hard": at a modest penalty the anchors land *near* their targets
    and measurably not *on* them."""
    solver = prefactor(graph, anchors, constraint="soft", penalty=10.0)
    positions = solve_positions(solver, graph, identity_rotations, anchors)

    error = np.abs(positions[anchors.indices] - TARGETS).max()
    assert error > 1e-6, "a soft constraint that lands exactly is a hard one"
    assert error < 0.5, "the anchors should still be pulled toward their targets"


def test_raising_the_penalty_tightens_the_pull(graph, anchors, identity_rotations):
    """Monotonicity is the honest statement of what the penalty does, and it is
    what a reader would want to know before choosing one. Asserted across three
    decades so the test says "tightens" rather than "differs"."""

    def anchor_error(penalty):
        solver = prefactor(graph, anchors, constraint="soft", penalty=penalty)
        positions = solve_positions(solver, graph, identity_rotations, anchors)
        return np.abs(positions[anchors.indices] - TARGETS).max()

    errors = [anchor_error(p) for p in (1.0, 10.0, 100.0, 1000.0)]
    assert errors == sorted(errors, reverse=True), errors


def test_a_large_penalty_converges_on_the_hard_solution(
    graph, anchors, identity_rotations
):
    """The limit the two styles share, which is what says they are two ways of
    imposing the same constraint rather than two different constraints."""
    hard = solve_positions(
        prefactor(graph, anchors), graph, identity_rotations, anchors
    )
    soft = solve_positions(
        prefactor(graph, anchors, constraint="soft", penalty=1e9),
        graph,
        identity_rotations,
        anchors,
    )
    np.testing.assert_allclose(soft, hard, atol=1e-6)


def test_the_solver_reports_the_style_it_was_built_with(graph, anchors):
    """`solve_positions` branches on `solver.constraint`, so the field is load
    bearing rather than informational — a Solver that misreported it would apply
    the wrong right-hand side."""
    assert prefactor(graph, anchors).constraint == "hard"

    soft = prefactor(graph, anchors, constraint="soft", penalty=25.0)
    assert soft.constraint == "soft"
    assert soft.penalty == 25.0
