"""Is the in-run wiring assertion's SILENCE evidence, or an uninterpreted fact?

The ρ = 32 and ρ = 64 runs carried a non-tautological T0.1 assertion block and it
did not fire. On its own that says nothing: an assertion that *cannot* fire is
silent too, and this project has already retracted one such assertion as evidence
(`phase_b_probe_verdict.md`, 2026-07-29). This file makes the silence mean
something, by driving the block against deliberately broken rules and recording
which arm catches what.

**What the block is.** Inside `deform_splat.py`, immediately before the real
scaling call, at ρ = 2 — a value in the branch where the declared failure modes
live, not at the ρ = 1 no-op that made the earlier assertion tautological:

    _R = (_rl == 1)
    _rr = _R[:, None] & _R[indices_knn]
    assert _rr.any(),                                          # T0.1a
    _probe = rho_scale_weights(weight, indices_knn, _rl, 2.0)
    assert torch.equal(_probe[~_rr], weight[~_rr]),            # T0.1b
    assert torch.allclose(_probe[_rr], 2.0 * weight[_rr]),     # T0.1c

**Where faults are injected, and why it must be there.** At the *rule*, never at
the assertion's arguments. The caller derives `_R` from the same `_rl` array it
passes down to the rule, so permuting that array moves both sides together — an
argument-level fault proves nothing about what the block can observe. The rule is
therefore the only place a fault is visible to it, and it is injected by supplying
a different callable for the name the archived code resolves from its import.

**Transcribed, not extracted.** The block is inline statements inside a method, not
a named function, so there is nothing to import. `test_each_transcribed_fragment…`
below is what keeps the transcription honest: every fragment must appear verbatim
in the archived patched source *and* in this module's own source. That preserves
the conformance suite's discipline — a test binds to archived text, not to a copy
nobody rechecks — without statement-level extraction machinery.

**Deliberately outside this file: the label frame.** It is closed by construction,
not by measurement, and `test_a_permuted_label_frame_stays_silent` records that as
a finding rather than hiding it.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest

import torch

from plan1.provenance import EVIDENCE_ROOT, require_vendored, sha256_file

#: The vendored evidence base. This used to be a checkout outside this repository,
#: which made this whole module skip on any machine that did not have one.
ARCHIVE = EVIDENCE_ROOT

#: The call site that ran ρ = 32 and ρ = 64. Archived byte-exact; the manifest cites
#: this content hash as provenance for those two rows.
PATCHED_CALL_SITE = ARCHIVE / "cluster" / "sources_20260805_patched" / "deform_splat.py"
PATCHED_SHA256 = "e2ca10cf4ef7ae00b36cdc9a0baa30518ce028aef0ec37ce75a6c112919ed397"

#: The rule the block probes. Unpatched between the sweep runs and the saturation
#: runs — preflight compared all six sources and found 6/6 sha256 MATCH — so the
#: archived 2026-07-29 copy *is* the rule that ran on 2026-08-05.
CLUSTER_HELPER = ARCHIVE / "cluster" / "sources_20260729" / "helper.py"

require_vendored(PATCHED_CALL_SITE, "the patched rho = 32/64 call site")
require_vendored(CLUSTER_HELPER, "the deployed rigidity rule")


def load_cluster_function(path: Path, name: str):
    """Compile one function out of an archived cluster source, by AST.

    Same mechanism as the conformance suite: only the named function is compiled,
    so none of the module's imports or side effects run, and the binding is to the
    archived *text*.
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


archived_rule = load_cluster_function(CLUSTER_HELPER, "rho_scale_weights")


# ── the block, as one callable ──────────────────────────────────────────────
#: What each arm is for, in the archived source's own words.
ARMS = {
    "T0.1a": "partition produced no R-R interior edge",
    "T0.1b": "non-R-R edges perturbed",
    "T0.1c": "R-R scale wrong (renormalised? bad indices_knn gather? label frame?)",
}


def run_wiring_assertion(weight, indices_knn, _rl, rho_scale_weights) -> str | None:
    """The archived assertion block, driven as one unit. Returns the arm that fired.

    Local names are the archived ones deliberately, so the transcription is literal
    rather than a paraphrase — including the injected `rho_scale_weights`, which is
    exactly the name the archived code resolves from `util.helper`. `assert X, msg`
    becomes `if not X: return arm` so a harness can see *which* arm caught a fault;
    the conditions themselves are untouched.
    """
    _R = (_rl == 1)
    _rr = _R[:, None] & _R[indices_knn]
    if not _rr.any():
        return "T0.1a"
    _probe = rho_scale_weights(weight, indices_knn, _rl, 2.0)
    if not torch.equal(_probe[~_rr], weight[~_rr]):
        return "T0.1b"
    if not torch.allclose(_probe[_rr], 2.0 * weight[_rr]):
        return "T0.1c"
    return None


#: Every condition the block tests, exactly as the archived file spells it. Both
#: the archived source and this module must contain each one verbatim.
TRANSCRIBED_FRAGMENTS = (
    "_R = (_rl == 1)",
    "_rr = _R[:, None] & _R[indices_knn]",
    "_rr.any()",
    "_probe = rho_scale_weights(weight, indices_knn, _rl, 2.0)",
    "torch.equal(_probe[~_rr], weight[~_rr])",
    "torch.allclose(_probe[_rr], 2.0 * weight[_rr])",
)


# ── the graph the block is driven over ──────────────────────────────────────
def rbf_graph(n=64, k=6, rigid_fraction=0.5, seed=0):
    """A KNN adjacency with ROW-NORMALISED weights, plus a two-region labelling.

    Row normalisation matters: the deployed rule's docstring warns that
    renormalising after scaling would cancel ρ on interior rows, and that failure
    mode is only faithfully modelled if the rows summed to one to begin with.
    """
    rng = np.random.default_rng(seed)
    indices = np.stack([rng.permutation(n)[:k] for _ in range(n)])
    weights = rng.uniform(0.05, 2.0, size=(n, k))
    weights = weights / weights.sum(axis=1, keepdims=True)
    labels = (rng.random(n) < rigid_fraction).astype(np.int64)  # 0 = base, 1 = rigid
    return (
        torch.tensor(weights, dtype=torch.float64),
        torch.tensor(indices, dtype=torch.long),
        torch.tensor(labels, dtype=torch.long),
    )


# ── the injected faults, all at the rule ────────────────────────────────────
def renormalising_rule(weight, indices_knn, region_label, rho, rigid_id=1):
    """Declared failure mode 1: renormalise after scaling, cancelling ρ."""
    scaled = archived_rule(weight, indices_knn, region_label, rho, rigid_id)
    return scaled / scaled.sum(dim=1, keepdim=True)


def mis_gathering_rule(weight, indices_knn, region_label, rho, rigid_id=1):
    """Declared failure mode 2: gather neighbour labels through a rolled index."""
    return archived_rule(
        weight, torch.roll(indices_knn, 1, dims=1), region_label, rho, rigid_id
    )


def wrong_rigid_id_rule(weight, indices_knn, region_label, rho, rigid_id=1):
    """Beyond the declared modes: scale the *base* region instead of the rigid one."""
    return archived_rule(weight, indices_knn, region_label, rho, rigid_id=0)


def mis_scaling_rule(weight, indices_knn, region_label, rho, rigid_id=1):
    """Beyond the declared modes: right edges, wrong magnitude."""
    return archived_rule(weight, indices_knn, region_label, rho * rho, rigid_id)


# ── the check is not vacuous ────────────────────────────────────────────────
def test_the_assertion_is_silent_on_the_correct_rule():
    """Without this, everything below would be consistent with a check that always
    fires — which is no more informative than one that never can."""
    weight, indices_knn, _rl = rbf_graph()
    assert run_wiring_assertion(weight, indices_knn, _rl, archived_rule) is None


@pytest.mark.parametrize("seed", range(6))
def test_silence_on_the_correct_rule_is_not_a_property_of_one_graph(seed):
    weight, indices_knn, _rl = rbf_graph(n=100, k=8, seed=seed)
    assert run_wiring_assertion(weight, indices_knn, _rl, archived_rule) is None


# ── reachability: which arm catches what ────────────────────────────────────
@pytest.mark.parametrize(
    "rule, expected_arm",
    [
        pytest.param(renormalising_rule, "T0.1b", id="renormalises-after-scaling"),
        pytest.param(mis_gathering_rule, "T0.1b", id="mis-gathered-neighbour-index"),
        pytest.param(wrong_rigid_id_rule, "T0.1b", id="wrong-rigid-region-id"),
        pytest.param(mis_scaling_rule, "T0.1c", id="mis-scaled-rigid-interior"),
    ],
)
@pytest.mark.parametrize("seed", range(4))
def test_an_injected_fault_fires_and_names_its_arm(rule, expected_arm, seed):
    """Each fault is attributed to one arm, so no arm is carried as dead weight.

    Across several graphs, because an arm that caught a fault on one lucky
    adjacency would be a weaker claim than the reachability table records.
    """
    weight, indices_knn, _rl = rbf_graph(n=100, k=8, seed=seed)
    assert run_wiring_assertion(weight, indices_knn, _rl, rule) == expected_arm


def test_an_empty_rigid_interior_fires_the_first_arm():
    """Not an injected fault — a degenerate *input*, which is what T0.1a is for.

    With no rigid anchors the probe would scale nothing, and the two remaining arms
    would pass on an entirely inert rule. T0.1a is what stops that reading.
    """
    weight, indices_knn, _rl = rbf_graph()
    assert run_wiring_assertion(weight, indices_knn, _rl * 0, archived_rule) == "T0.1a"


def test_every_arm_of_the_block_is_reachable():
    weight, indices_knn, _rl = rbf_graph()
    fired = {
        run_wiring_assertion(weight, indices_knn, _rl * 0, archived_rule),
        run_wiring_assertion(weight, indices_knn, _rl, renormalising_rule),
        run_wiring_assertion(weight, indices_knn, _rl, mis_scaling_rule),
    }
    assert fired == set(ARMS)


# ── the one thing it cannot see, recorded rather than hidden ────────────────
def test_a_permuted_label_frame_stays_silent():
    """The unsatisfiable acceptance criterion, demonstrated as unsatisfiable.

    A label-frame mismatch cannot make this block fire, and no harness can make it:
    the caller derives `_R` from the same `_rl` it passes to the rule, so permuting
    the array moves both sides together and the probe agrees with the recomputed
    mask exactly as before. This is not a gap in the harness — it is a property of
    the block, and it is why the criterion demanding this demonstration is amended
    rather than dropped.

    What the block *does* deliver in that territory is T0.1a: the rigid interior is
    non-empty, so the labelling is at least not degenerate. The residual — that the
    labels are in the same frame as the weights — is closed by construction and is
    named as an out-of-scope check in the verdict.
    """
    weight, indices_knn, _rl = rbf_graph()
    permuted = torch.roll(_rl, 7)
    assert run_wiring_assertion(weight, indices_knn, permuted, archived_rule) is None
    # and the permutation was not a no-op that made the test vacuous
    assert not torch.equal(permuted, _rl)


def test_the_partition_never_reads_the_drag_target():
    """The information asymmetry, verifiable in the archived source.

    The rigidity field is derived from the anchor set and the mean of the authored
    drag *source* only. `drag_target_filtered` — the observed motion — exists in the
    same scope and never reaches it, so the method's rigidity never sees the motion
    the baseline is given. Read off the source rather than asserted in prose.
    """
    source = PATCHED_CALL_SITE.read_text()
    assignments = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith("_rl = ")
    ]
    assert len(assignments) == 1, assignments
    call = assignments[0]
    assert "partition_anchors_by_handle(anchor, points_3d_filtered.mean(0)" in call
    assert "drag_target" not in call


# ── the drift guard: a transcription that cannot silently diverge ───────────
@pytest.mark.parametrize("fragment", TRANSCRIBED_FRAGMENTS)
def test_each_transcribed_fragment_appears_verbatim_in_the_archived_source(fragment):
    assert fragment in PATCHED_CALL_SITE.read_text(), fragment


@pytest.mark.parametrize("fragment", TRANSCRIBED_FRAGMENTS)
def test_each_transcribed_fragment_appears_verbatim_in_the_harness(fragment):
    """Both ends of the binding. Without this the fragment list could drift from
    the callable it claims to describe while still matching the archive."""
    assert fragment in inspect.getsource(run_wiring_assertion), fragment


def test_the_archived_call_site_is_the_version_the_manifest_cites():
    """The whole point of fetching it: the provenance citation is now checkable by
    a reader who never had cluster access."""
    assert sha256_file(PATCHED_CALL_SITE) == PATCHED_SHA256
