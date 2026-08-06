"""Conformance — does the DEPLOYED rigidity rule match the TESTED reference?

The Phase-B verdict certifies the imposed-rigidity knob as *live* but explicitly
**not** as correctly wired: the in-code identity assertion read
``torch.equal(weight, rho_scale_weights(weight, …, rho=1.0))``, and the helper
early-returns its input at unit rigidity, so it evaluated ``torch.equal(w, w)``. It
fired without error on every run, exactly as it would have with a completely broken
scaling path — none of the three failure modes it was the declared mitigation for
(renormalisation, a mis-gathered neighbour index, a label-frame mismatch) live in
that branch.

This suite checks the same rule from the other side, and it is what the
pre-registered wiring gate rests on locally (plan1_prereg.md §6):

* the **reference** is the method repository's tested ``scale_interior_edges``,
  **imported** rather than copied, so the test notices if the two ever diverge;
* the **deployed** rule is loaded out of the archived cluster source *text* by AST,
  so the test runs the code that actually produced the runs — not a transcription
  of it;
* the primary comparison is at **ρ ≠ 1**, deliberately: that is the branch where
  the three known failure modes live. The ρ = 1 no-op is asserted too, but as a
  secondary invariant, never as the evidence.

The two rules differ in data layout — the reference takes an edge list, the cluster
a K-nearest-neighbour adjacency — which is exactly why agreement edge-for-edge is
worth asserting rather than assuming.

**Deliberately outside this suite: the cluster-side pass-through wrapper**
(`sweep_rho.py`, and the `deform_splat.py` call site that hands `weight` to the
rule). It loads and passes through, and nothing else. It cannot be exercised by a
local suite — it needs the node, the container image and a GPU — so keeping it
logic-free is the mitigation rather than a test. What *is* checkable locally is the
rule it calls, which is what this file does. A reader should not read a green run
here as evidence about the wrapper.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from plan1.provenance import head_commit, sha256_file

torch = pytest.importorskip("torch", reason="the deployed rule is written in torch")

from box_b.edge_weights import scale_interior_edges  # noqa: E402  (after importorskip)

#: The archived cluster sources — the code that produced the runs in
#: `3D/cluster/rho_probe_evidence/`.
CLUSTER_HELPER = (
    Path(__file__).resolve().parents[2] / "3D" / "cluster" / "sources_20260729" / "helper.py"
)
METHOD_REPO = Path(__file__).resolve().parents[2] / "arap-deform-3dgs"

pytestmark = pytest.mark.skipif(
    not CLUSTER_HELPER.is_file(),
    reason=f"archived cluster source not present at {CLUSTER_HELPER}",
)


def load_cluster_rule(path: Path, name: str = "rho_scale_weights"):
    """Compile one function out of the archived cluster source, by AST.

    Only the named function is compiled, so none of the module's imports or
    side effects run. The binding is to the archived *text*: if that file changes,
    this test runs the changed rule.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            module = ast.Module(body=[node], type_ignores=[])
            code = compile(ast.fix_missing_locations(module), str(path), "exec")
            namespace: dict = {"torch": torch}
            exec(code, namespace)  # noqa: S102 — archived source under test
            return namespace[name]
    raise AssertionError(f"{path} does not define {name}()")


rho_scale_weights = load_cluster_rule(CLUSTER_HELPER)

RIGID_ID = 1


# ── the bridge between the two data layouts ─────────────────────────────────
def knn_graph(n=64, k=6, stiff_fraction=0.4, seed=0):
    """A random KNN adjacency plus a two-region labelling."""
    rng = np.random.default_rng(seed)
    indices = np.stack([rng.permutation(n)[:k] for _ in range(n)])
    weights = rng.uniform(0.05, 2.0, size=(n, k))
    labels = (rng.random(n) < stiff_fraction).astype(np.int64)  # 0 = base, 1 = rigid
    return weights, indices, labels


def apply_reference(weights, indices, labels, rho):
    """Drive the method repository's rule over the same graph, edge for edge.

    The KNN adjacency is unrolled into one directed edge per (row, neighbour)
    slot. ``scale_interior_edges`` keys purely off the labels at each endpoint, so
    a directed edge list is a faithful presentation of the same graph.
    """
    n, k = indices.shape
    edges = np.stack(
        [np.repeat(np.arange(n), k), np.asarray(indices).reshape(-1)], axis=1
    )
    scaled = scale_interior_edges(
        np.asarray(weights, dtype=np.float64).reshape(-1),
        edges,
        np.asarray(labels),
        np.array([1.0, float(rho)]),  # region 0 is base, region 1 carries rho
    )
    return scaled.reshape(n, k)


def apply_cluster(weights, indices, labels, rho):
    out = rho_scale_weights(
        torch.tensor(weights, dtype=torch.float64),
        torch.tensor(indices, dtype=torch.long),
        torch.tensor(labels, dtype=torch.long),
        rho,
        rigid_id=RIGID_ID,
    )
    return out.numpy()


# ── the primary check: the two rules agree, edge for edge ───────────────────
@pytest.mark.parametrize("rho", [0.0625, 0.25, 2.0, 4.0, 16.0, 32.0, 64.0])
def test_deployed_rule_matches_the_tested_reference_edge_for_edge(rho):
    weights, indices, labels = knn_graph()
    np.testing.assert_array_equal(
        apply_cluster(weights, indices, labels, rho),
        apply_reference(weights, indices, labels, rho),
    )


@pytest.mark.parametrize("seed", range(6))
def test_agreement_holds_across_graphs(seed):
    weights, indices, labels = knn_graph(n=100, k=8, seed=seed)
    np.testing.assert_array_equal(
        apply_cluster(weights, indices, labels, 16.0),
        apply_reference(weights, indices, labels, 16.0),
    )


@pytest.mark.parametrize("stiff_fraction", [0.0, 1.0])
def test_agreement_holds_at_the_degenerate_labellings(stiff_fraction):
    """No rigid region at all, and everything rigid."""
    weights, indices, labels = knn_graph(stiff_fraction=stiff_fraction)
    np.testing.assert_array_equal(
        apply_cluster(weights, indices, labels, 16.0),
        apply_reference(weights, indices, labels, 16.0),
    )


# ── boundary-crossing edges are untouched, in both ──────────────────────────
def test_boundary_crossing_edges_keep_their_base_weight_in_both_rules():
    weights, indices, labels = knn_graph()
    rho = 16.0
    crossing = labels[:, None] != labels[np.asarray(indices)]

    for name, scaled in (
        ("cluster", apply_cluster(weights, indices, labels, rho)),
        ("reference", apply_reference(weights, indices, labels, rho)),
    ):
        np.testing.assert_array_equal(
            scaled[crossing], weights[crossing], err_msg=f"{name} touched a boundary edge"
        )
        # and the interior of the rigid region *was* scaled, or the test is vacuous
        interior = (labels[:, None] == RIGID_ID) & (
            labels[np.asarray(indices)] == RIGID_ID
        )
        assert interior.any()
        np.testing.assert_allclose(scaled[interior], weights[interior] * rho)


# ── unit rigidity: a byte-exact no-op through both (secondary) ──────────────
def test_unit_rigidity_is_a_byte_exact_noop_through_both():
    """Asserted as an invariant, NOT as wiring evidence.

    The cluster rule early-returns at ρ = 1, so this cannot distinguish a correct
    scaling path from a broken one — that is precisely the tautology the Phase-B
    verdict retracted. The evidence is the ρ ≠ 1 agreement above.
    """
    weights, indices, labels = knn_graph()
    np.testing.assert_array_equal(apply_cluster(weights, indices, labels, 1.0), weights)
    np.testing.assert_array_equal(apply_reference(weights, indices, labels, 1.0), weights)


# ── negative controls: the check must be able to fail ───────────────────────
def test_the_conformance_check_catches_renormalisation():
    """Failure mode 1: renormalising after scaling cancels ρ on interior rows."""
    weights, indices, labels = knn_graph()
    rho = 16.0
    correct = apply_cluster(weights, indices, labels, rho)

    renormalised = correct / correct.sum(axis=1, keepdims=True)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(
            renormalised, apply_reference(weights, indices, labels, rho)
        )


def test_the_conformance_check_catches_a_mis_gathered_neighbour_index():
    """Failure mode 2: gathering the neighbour labels through the wrong index."""
    weights, indices, labels = knn_graph()
    rho = 16.0
    mis_gathered = apply_reference(weights, np.roll(indices, 1, axis=1), labels, rho)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(
            mis_gathered, apply_reference(weights, indices, labels, rho)
        )


def test_the_conformance_check_catches_a_label_frame_mismatch():
    """Failure mode 3: the labels are in a different frame from the weights."""
    weights, indices, labels = knn_graph()
    rho = 16.0
    permuted = apply_reference(weights, indices, np.roll(labels, 7), rho)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(
            permuted, apply_reference(weights, indices, labels, rho)
        )


def test_the_conformance_check_catches_scaling_every_edge():
    """The crudest break: scale everything rather than the region interior."""
    weights, indices, labels = knn_graph()
    rho = 16.0
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(
            weights * rho, apply_reference(weights, indices, labels, rho)
        )


# ── provenance: which versions did this test bind to? ───────────────────────
def test_both_rules_are_identifiable_by_content():
    """A passing check is only evidence if the checked versions are nameable."""
    import box_b.edge_weights as reference_module

    reference_path = Path(reference_module.__file__)
    assert sha256_file(reference_path)
    assert sha256_file(CLUSTER_HELPER)
    # the method repo's commit is recorded where it is resolvable; a bare checkout
    # reports unknown rather than guessing
    head_commit(METHOD_REPO)
