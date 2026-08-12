"""The vendored evidence is auditable against the originals it was copied from.

Vendoring gives up divergence detection — a copy cannot notice that its original
moved. `evidence/PROVENANCE.toml` is what is offered in exchange: for every copied
byte, what it is and what it hashes to, so a reader holding an original can check the
copy against it.

That record is only worth anything if it is asserted **in both directions**. A row
whose file has changed must fail; so must a file that arrived with no row. The
second half is the one that matters in practice — a one-directional check lets
evidence accumulate quietly, unrecorded and unexplained, which is the state this
whole repository is escaping from.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from audit import (
    AUTHORED_UNDER_EVIDENCE,
    HOME_MARKERS,
    PRIVATE_REPOS,
    forbidden_references,
    origin_problems,
)
from plan1.provenance import (
    EVIDENCE_ROOT,
    REPO_ROOT,
    VendoredFile,
    load_evidence,
    sha256_file,
)

RECORD = load_evidence()

#: The hash the manifest cites for the rho = 32/64 rows, and that the wiring
#: harness pins independently. Restated here so the vendored copy is checked
#: against the *published citation* and not only against its own record.
PATCHED_SHA256 = "e2ca10cf4ef7ae00b36cdc9a0baa30518ce028aef0ec37ce75a6c112919ed397"


def vendored_files() -> list[Path]:
    """Every *copied* file under `evidence/`.

    Two files there are this repository's own — the manifest, and the note that
    classifies the vendored records' links — so neither has an original to be
    audited against and neither carries a row. They are named in `tests/audit.py`,
    which also owns the other half of the same distinction: those two are audited
    for forbidden references and the copies are not. One list, so "what needs a row"
    and "what gets audited" cannot drift into disagreement.
    """
    authored = {REPO_ROOT / relative for relative in AUTHORED_UNDER_EVIDENCE}
    return sorted(
        path
        for path in EVIDENCE_ROOT.rglob("*")
        if path.is_file() and path not in authored and path.name != ".DS_Store"
    )


# ── the record describes what is there ──────────────────────────────────────
@pytest.mark.parametrize("entry", RECORD.files, ids=lambda e: e.path)
def test_every_vendored_file_hashes_to_its_recorded_value(entry):
    path = RECORD.resolve(entry.path)
    assert path.is_file(), f"{entry.path} is recorded but absent"
    assert sha256_file(path) == entry.sha256


@pytest.mark.parametrize("entry", RECORD.files, ids=lambda e: e.path)
def test_every_row_says_what_the_file_is_and_why_it_travelled(entry):
    """A hash alone is not provenance. Without knowing what the file *is*, a reader
    cannot judge whether it supports the sentence citing it; without a reason,
    nobody can tell whether it should be here at all.

    **This assertion used to require the opposite.** It read
    `assert entry.source.startswith(…)` against a leading tilde-and-separator — it
    *mandated* that every row name a directory on the authoring machine, and 55 rows
    obliged. That is how the leak was not merely tolerated but enforced: cleaning it
    up had to start by watching this line fail. It did, on 2026-08-08, 49 times, with
    `AttributeError: 'VendoredFile' object has no attribute 'source'`.

    What replaces it is the property a reader actually wants — the origin says what
    the measurement is, and says it without reaching for a path, a repository or a
    ticket that they cannot resolve.
    """
    assert entry.why, f"{entry.path} has no reason for travelling"
    problems = origin_problems(entry.origin)
    assert not problems, (
        f"{entry.path}'s origin is {entry.origin!r}:\n  " + "\n  ".join(problems)
    )


@pytest.mark.parametrize(
    "bad_origin",
    [
        "",
        HOME_MARKERS[0] + "3D/cluster/rho_probe_evidence/penguin_rho16/stats/x.json",
        "copied out of " + PRIVATE_REPOS[0],
        "vendored under " + "#" + "15",
        "cluster/rho_probe_evidence/penguin_rho16/stats/val_step0501.json",
    ],
    ids=["empty", "home path", "private repository", "ticket", "bare path"],
)
def test_the_origin_guard_fails_on_a_row_that_names_something_unreachable(bad_origin):
    """The guard above, driven against a deliberately bad row.

    A guard nobody has watched fail is a guard nobody knows the failure mode of, and
    this one replaced an assertion that could not fail in the useful direction — it
    demanded the leak. So the five ways a row can be wrong are each put to it here,
    which is the practice `tests/test_conformance.py`'s negative controls establish
    for the wiring gate.

    The real guard is *called*, not reimplemented. A negative control that asserted
    against its own copy of the predicate would pass while the guard itself was
    edited into uselessness.
    """
    bad = VendoredFile(
        path="cluster/rho_probe_evidence/penguin_rho16/stats/val_step0501.json",
        origin=bad_origin,
        sha256="0" * 64,
        why="a reason that is present, so the origin is what fails",
    )
    with pytest.raises(AssertionError):
        test_every_row_says_what_the_file_is_and_why_it_travelled(bad)


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
    """Both checks above pass trivially against an empty directory.

    64 = 39 run/cluster + 21 characterisation + 4 documents. The 39: **sixteen** run
    directories × two stats files = 32, four run logs, two archived cluster sources,
    one spike console. The 21: every characterisation artifact except a `.DS_Store` —
    seventeen were scoped up front, and the four beyond them are each the input a
    named document asserts against, so they travelled too. The 4: the
    pre-registration and the verdict, cited sixteen times and shipped zero times,
    plus the two companions those two cite by name — the Phase-B probe verdict and
    the feasibility addendum, whose sibling-relative citations resolved nowhere
    until the documents landed beside them. All departures are on the record in
    `PROVENANCE.toml`.

    **It was 49, over nine run directories and three logs.** The second asset's seven
    directories were excluded on the stated grounds that no manifest row bound them
    and no published number derived from them; `manifests/trex_deformsplat.toml` now
    binds all seven, so both halves of that reason expired at once and the exclusion
    was deleted rather than left standing beside the rows it denies. The fourth log
    travelled with them: it is the only surviving record of what command produced
    that sweep, and it was excluded for precisely that reason back when the rows it
    describes were not here.
    """
    assert len(RECORD.files) == len(vendored_files()) == 64


# ── the characterisation outputs carry what a derived artefact needs ────────
#: Every CSV the results chapter cites, and the line count it must have. A copy
#: truncated in transit still parses, still hashes to *something*, and still draws
#: a figure — it just draws a different one. Counting lines is the cheap check that
#: catches it as a wrong number rather than as a missing file. Counts are
#: `wc -l`: one header plus the data rows.
CHARACTERISATION_ROWS = {
    "characterisation/item2_mask/mask_grid.csv": 393,
    "characterisation/item1_kgamma/kgamma_summary.csv": 433,
    "characterisation/item2_mask/rswing_geometry.csv": 288,
    "characterisation/item1_kgamma/kgamma_controllability.csv": 49,
    "characterisation/item2_mask/rswing_support.csv": 41,
}


def characterisation_files() -> list[VendoredFile]:
    return [e for e in RECORD.files if e.path.startswith("characterisation/")]


@pytest.mark.parametrize(
    "entry", characterisation_files(), ids=lambda e: e.path
)
def test_every_characterisation_output_names_its_command_date_and_verdict(entry):
    """A run record is its own evidence; a derived artefact is not.

    `val_step0501.json` came off the cluster and means what it says. A figure or a
    summary CSV is the output of a program, and a reader who cannot see which
    program, when it ran, and which verdict checked the result has no way to tell
    whether the file still supports the sentence citing it. Three fields rather than
    three sentences of prose.
    """
    assert entry.command, f"{entry.path} has no generating command"
    assert entry.generated, f"{entry.path} has no generation date"
    assert entry.certified_by, f"{entry.path} names no certifying verdict"


@pytest.mark.parametrize(
    "path,expected", sorted(CHARACTERISATION_ROWS.items()), ids=lambda v: str(v)
)
def test_the_cited_csvs_have_the_row_counts_their_verdicts_recomputed_from(
    path, expected
):
    """A truncated copy is caught as a wrong number, not shipped as a right one."""
    actual = len(RECORD.resolve(path).read_text().splitlines())
    assert actual == expected


def test_the_three_verdict_counts_are_what_the_verdicts_actually_say():
    """`README.md` publishes 11/11, 17/17 and 9/9 where a reader lands.

    Quoting a count into a second document is how a count goes stale. This reads
    the number back out of the file it describes, so the published claim and the
    vendored bytes cannot drift apart silently.
    """
    for path, expected in (
        ("characterisation/item1_kgamma/KGAMMA_VERDICT.md", 11),
        ("characterisation/item2_mask/MASK_VERDICT.md", 17),
        ("characterisation/reporting/FIGURE_CHECK.md", 9),
    ):
        text = RECORD.resolve(path).read_text()
        assert text.count("| PASS") == expected, path
        assert f"{expected}/{expected}" in text, path


# ── the two documents the artefact argues from ──────────────────────────────
#: Cited sixteen times across this repository and shipped zero times until vendored —
#: including in the published table's own byline, which named a path in an archive
#: no reader could reach.
RECORD_DOCS = {
    "record/plan1_prereg.md": "pre-registration",
    "record/plan1_verdict.md": "verdict",
}


@pytest.mark.parametrize("path", sorted(RECORD_DOCS))
def test_the_governing_documents_travelled(path):
    assert RECORD.resolve(path).is_file(), path
    assert RECORD.resolve(path).read_text().strip(), f"{path} is empty"


@pytest.mark.parametrize("path", sorted(RECORD_DOCS))
def test_each_governing_document_pins_the_archive_revision_it_came_from(path):
    """Bytes alone are not enough for a document.

    A run record is its own evidence and a hash is all it needs. A pre-registration
    is a claim about what was decided, so *which revision travelled* has to be
    answerable — otherwise a reader cannot tell the shipped copy from a later one
    that says something more convenient.
    """
    entry = next(e for e in RECORD.files if e.path == path)
    assert re.fullmatch(r"[0-9a-f]{40}", entry.archive_commit or ""), entry.archive_commit
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.archive_date or ""), entry.archive_date


def test_the_pre_registration_records_when_it_was_added_not_only_when_it_moved():
    """Two dates, because one of them alone reads backwards.

    `archive_date` is the revision that travelled: 2026-08-06, which is *after* the
    2026-08-05 runs and looks like the rule was written to fit them. `archive_first_date`
    is when the file was added — 2026-08-05, in the commit that also carried the
    cluster handoff that dispatched those runs. Same day, not the day after.

    Same-day granularity still cannot prove precedence and this is not asked to. It
    removes a false impression; `test_archived_sweep_as_it_stands_is_not_saturated`
    is what carries the claim.
    """
    entry = next(e for e in RECORD.files if e.path == "record/plan1_prereg.md")
    assert re.fullmatch(r"[0-9a-f]{40}", entry.archive_first_commit or "")
    assert entry.archive_first_date == "2026-08-05"
    assert entry.archive_first_date <= (entry.archive_date or ""), (
        "the file cannot have been added after the revision that travelled"
    )


def test_only_the_governing_documents_claim_an_archive_revision():
    claimed = {e.path for e in RECORD.files if e.archive_commit is not None}
    assert claimed == set(RECORD_DOCS)


def test_the_archive_date_is_not_offered_as_precedence_evidence():
    """The trap in the recorded dates, written down so it cannot be reintroduced.

    The archive commit is dated 2026-08-06. The runs the pre-registration licensed
    are dated 2026-08-05 — one day EARLIER — because it is the last commit that
    touched the file, not the day the rule was written. Anyone reading that date as
    "the rule came first" would be reading it backwards.

    Precedence is carried by `test_archived_sweep_as_it_stands_is_not_saturated`
    instead: the rule, applied to the sweep as it stood when it was written, returns
    NOT SATURATED and demands rho = 32. It forced work rather than ratifying it. This
    test asserts the distinction is stated where the date is, so the two can never
    drift apart.
    """
    text = (EVIDENCE_ROOT / "PROVENANCE.toml").read_text()
    assert "NOT the date the pre-registration was written" in text
    assert "test_archived_sweep_as_it_stands_is_not_saturated" in text


def test_the_published_byline_cites_a_path_that_exists_in_this_repository():
    """The defect the vendoring exists for, asserted rather than fixed and forgotten.

    The byline used to send a reader to
    `all_record/deformsplat_corroboration/plan1_prereg.md`, which is in an archive
    they do not have. A citation that resolves nowhere is worse than none: it claims
    the rules were fixed in advance while making the claim uncheckable.

    Scoped to the whole package rather than to `render.py`. Bound to the byline
    alone, this passed while `saturation.py`, `assemble.py` and `__init__.py` still
    sent a reader to the archive path in their module docstrings — including the
    module that implements the pre-registered rule, which is the file most likely to
    be opened. A guard that covers one instance of a defect the repository claims to
    have closed is how the other three survived being fixed.
    """
    from plan1 import render

    # `render.py` keeps the old path in a comment that explains why it moved. That
    # sentence is the record of the fix, so it is whitelisted by exact text rather
    # than by exempting the file — anything else in it still fails.
    historical = "# The byline used to cite `all_record/deformsplat_corroboration/plan1_prereg.md`"

    package = Path(render.__file__).parent
    offenders = [
        str(path.relative_to(EVIDENCE_ROOT.parent))
        for path in sorted(package.glob("*.py"))
        if "all_record/deformsplat_corroboration" in path.read_text().replace(historical, "")
    ]
    assert not offenders, (
        f"these cite the pre-registration at a path no reader of this repository "
        f"can reach; it is vendored at evidence/record/plan1_prereg.md: {offenders}"
    )

    cited = "evidence/record/plan1_prereg.md"
    assert cited in Path(render.__file__).read_text()
    assert (EVIDENCE_ROOT.parent / cited).is_file()


def test_the_committed_table_cites_the_vendored_pre_registration():
    """The rendered artefact, not just the renderer. `out/comparison_table.md` is
    what a reader actually opens."""
    table = (EVIDENCE_ROOT.parent / "out" / "comparison_table.md").read_text()
    assert "evidence/record/plan1_prereg.md" in table
    assert "all_record/" not in table


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
    exactly the external dependency the vendoring removed."""
    assert RECORD.resolve(entry.path).is_relative_to(EVIDENCE_ROOT)


# ── the artefacts the footer names ──────────────────────────────────────────
def test_every_recorded_artefact_identifies_content_that_is_in_this_repository():
    """The footer may only cite things a reader can inspect.

    There used to be a second row here: `method repository HEAD`, a 40-hex commit in
    a repository nobody outside the project can clone. It was published in the one
    table where every line is meant to be checkable, and it was the only line that
    was not. Asserting the *set* rather than a minimum is what keeps it from coming
    back — a new row has to be argued for here before it can be printed.
    """
    names = {artefact.name for artefact in RECORD.artefacts}
    assert names == {"reference rule (`box_b/edge_weights.py`)"}
    for artefact in RECORD.artefacts:
        assert artefact.kind == "file_sha256", artefact.kind
        assert re.fullmatch(r"[0-9a-f]{64}", artefact.value), artefact.value
        assert artefact.why
        findings = forbidden_references(artefact.origin)
        assert not findings, [str(finding) for finding in findings]


# ── exclusions are stated, not left as an absence ───────────────────────────
def test_what_did_not_travel_is_recorded_with_a_reason():
    """"The evidence base" has to be a closed statement. The archive directory
    also held 1.4 MB of a second asset's logs; that they are absent is a decision,
    and a decision has to be readable.

    **That asset's sweep used to be on this list and is not any more.** It was
    excluded because no manifest row bound it; one does now, so the row was deleted
    rather than left contradicting the fourteen files it denies. An exclusion whose
    reason has expired is worse than no exclusion at all — it reads as a considered
    decision while describing a state of affairs that ended.
    """
    assert RECORD.excluded
    for entry in RECORD.excluded:
        assert entry.path and entry.reason
    assert any("trex" in entry.path for entry in RECORD.excluded)
