"""The vendored evidence is auditable against the archive it was copied from.

Vendoring gives up divergence detection — a copy cannot notice that its original
moved. `evidence/PROVENANCE.toml` is what is offered in exchange: source path and
sha256 for every copied byte, so a reader holding an original can check the copy
against it.

That record is only worth anything if it is asserted **in both directions**. A row
whose file has changed must fail; so must a file that arrived with no row. The
second half is the one that matters in practice — a one-directional check lets
evidence accumulate quietly, unrecorded and unexplained, which is the state this
whole repository is escaping from.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from plan1.provenance import EVIDENCE_ROOT, load_evidence, sha256_file

RECORD = load_evidence()

#: The hash the manifest cites for the rho = 32/64 rows, and that the wiring
#: harness pins independently. Restated here so the vendored copy is checked
#: against the *published citation* and not only against its own record.
PATCHED_SHA256 = "e2ca10cf4ef7ae00b36cdc9a0baa30518ce028aef0ec37ce75a6c112919ed397"


def vendored_files() -> list[Path]:
    """Every file actually present under `evidence/`, bar the record itself."""
    return sorted(
        path
        for path in EVIDENCE_ROOT.rglob("*")
        if path.is_file() and path.name != "PROVENANCE.toml" and path.name != ".DS_Store"
    )


# ── the record describes what is there ──────────────────────────────────────
@pytest.mark.parametrize("entry", RECORD.files, ids=lambda e: e.path)
def test_every_vendored_file_hashes_to_its_recorded_value(entry):
    path = RECORD.resolve(entry.path)
    assert path.is_file(), f"{entry.path} is recorded but absent"
    assert sha256_file(path) == entry.sha256


@pytest.mark.parametrize("entry", RECORD.files, ids=lambda e: e.path)
def test_every_row_names_where_it_came_from_and_why_it_travelled(entry):
    """A hash alone is not provenance. Without a source the copy cannot be
    audited, and without a reason nobody can tell whether it should be here."""
    assert entry.source.startswith("~/"), entry.source
    assert entry.why


# ── and what is there is described ──────────────────────────────────────────
def test_every_file_under_evidence_has_a_provenance_row():
    """The direction that is easy to omit and does all the work."""
    recorded = {RECORD.resolve(entry.path) for entry in RECORD.files}
    unrecorded = [
        str(path.relative_to(EVIDENCE_ROOT))
        for path in vendored_files()
        if path not in recorded
    ]
    assert not unrecorded, f"vendored with no provenance row: {unrecorded}"


def test_the_record_is_not_empty_in_a_way_that_would_make_this_vacuous():
    """Both checks above pass trivially against an empty directory."""
    assert len(RECORD.files) == len(vendored_files()) == 24


# ── the published citation, checked against the copy ────────────────────────
def test_the_vendored_call_site_hashes_to_the_value_the_manifest_cites():
    assert sha256_file(RECORD.resolve("cluster/sources_20260805_patched/deform_splat.py")) == (
        PATCHED_SHA256
    )


def test_the_two_gate_sources_travelled():
    """The conformance suite and the wiring harness both load these by AST out of
    the source text. If either is absent the gate does not run."""
    for path in (
        "cluster/sources_20260729/helper.py",
        "cluster/sources_20260805_patched/deform_splat.py",
    ):
        assert RECORD.resolve(path).is_file(), path


# ── the record stays inside the directory it describes ──────────────────────
@pytest.mark.parametrize("entry", RECORD.files, ids=lambda e: e.path)
def test_no_row_escapes_the_evidence_directory(entry):
    """`resolve()` follows `..`; a row that pointed outside would reintroduce
    exactly the external dependency this ticket removed."""
    assert RECORD.resolve(entry.path).is_relative_to(EVIDENCE_ROOT)


# ── the artefacts the footer names but does not vendor ──────────────────────
def test_the_recorded_artefacts_cover_the_method_repository():
    """Two footer rows identify the method repo, which is a separate port (#16).
    Their expected identities are recorded so a moved sibling is an error rather
    than a silently different table."""
    names = {artefact.name for artefact in RECORD.artefacts}
    assert names == {
        "reference rule (`box_b/edge_weights.py`)",
        "method repository HEAD",
    }
    for artefact in RECORD.artefacts:
        assert artefact.kind in {"file_sha256", "git_head"}
        assert artefact.value
        assert artefact.why


# ── exclusions are stated, not left as an absence ───────────────────────────
def test_what_did_not_travel_is_recorded_with_a_reason():
    """"The evidence base" has to be a closed statement. The archive directory
    also held a second asset's sweep and 1.4 MB of its logs; that they are absent
    is a decision, and a decision has to be readable."""
    assert RECORD.excluded
    for entry in RECORD.excluded:
        assert entry.path and entry.reason
    assert any("trex" in entry.path for entry in RECORD.excluded)
