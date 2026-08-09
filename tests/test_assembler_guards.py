"""What the assembler and its record reader refuse, and what they say when they do.

The guards here divide into two kinds and both are worth a test for the same
reason, which is that neither is reachable from the published path.

**Lookups that miss.** `ComparisonTable.row`, `EvidenceRecord.ported_file` and
`EvidenceRecord.artefact` each scan for a key and raise `KeyError` when there is
none. Every call in this repository passes a key that exists, so the raising
branch is only ever reached by a caller that has made a mistake — a test module
asking for a row by the wrong name, most likely. What matters is that it raises
rather than returning `None`, because a `None` would flow onward and fail later
somewhere that has forgotten what was being looked for.

**Inputs that are not what they claim.** A manifest row with an unknown `kind` or
an undeclared `root`, a run record missing a metric, a vendored file that is not
on disk. These are the assembler's contract with the data, and the data is
hand-written TOML — so these are the failures a person editing the manifest will
actually hit, and the message is the whole of what they get.

`plan1/provenance.py`'s `_require` is the one whose reason is written out at
length in the source: it raises rather than skipping, because a skip subtracts
from the total and leaves the summary line green.
"""

import re

import pytest

from plan1.assemble import assemble
from plan1.manifest import ManifestRow, load_records
from plan1.provenance import (
    EVIDENCE_ROOT,
    REPO_ROOT,
    display_path,
    load_evidence,
    require_vendored,
)
from plan1.records import Measurement, RunRecord

from conftest import make_manifest, make_record, make_row

RECORD = load_evidence()


# ── lookups that miss ───────────────────────────────────────────────────────
def test_asking_the_table_for_a_row_that_is_not_there_raises(
    three_row_case_full_precision,
):
    """`KeyError` and not `None`. A missing row returned as `None` would be read
    as "this row has no data" rather than "you asked for the wrong key"."""
    table = assemble(*three_row_case_full_precision)

    assert table.row("baseline").key == "baseline"
    with pytest.raises(KeyError, match="rho16"):
        table.row("rho16")


def test_asking_the_evidence_record_for_a_file_that_is_not_recorded_raises():
    assert RECORD.ported_file("box_b/edge_weights.py").path == "box_b/edge_weights.py"
    with pytest.raises(KeyError, match="box_b/descriptors.py"):
        RECORD.ported_file("box_b/descriptors.py")


def test_asking_the_evidence_record_for_an_artefact_that_is_not_recorded_raises():
    """The scan walks past the recorded artefact and then runs out, which is the
    only way this branch is taken — every call in this repository asks for the
    one name that is there."""
    assert RECORD.artefacts, "an empty artefact record makes the scan vacuous"
    assert RECORD.artefact(RECORD.artefacts[0].name) is RECORD.artefacts[0]

    with pytest.raises(KeyError, match="a name no artefact carries"):
        RECORD.artefact("a name no artefact carries")


# ── inputs that are not what they claim ─────────────────────────────────────
@pytest.mark.parametrize("kind", ["", "stats", "csv", "STATS_JSON"])
def test_a_manifest_row_with_an_unrecognised_kind_is_refused(kind):
    """`kind` selects the reader for the row's file. An unknown one has no reader,
    and the case-mismatched spelling is included because it is the mistake a
    person makes rather than the one a fuzzer does."""
    with pytest.raises(ValueError, match="kind must be one of"):
        ManifestRow(
            key="null",
            label="none",
            role="null",
            rigidity=None,
            information="—",
            kind=kind,
            root="fixture",
            path="null",
        )


def test_a_manifest_row_pointing_at_an_undeclared_root_is_refused(tmp_path):
    """Roots are declared once and referenced per row, so a typo in a row's root
    is a row that would silently resolve against nothing. Naming the declared
    roots in the message is what turns the failure into a correction."""
    manifest = make_manifest([make_row("null", "null")])
    manifest = type(manifest)(
        asset=manifest.asset,
        eval_step=manifest.eval_step,
        rows=manifest.rows,
        source=str(tmp_path / "manifest.toml"),
        assembled=manifest.assembled,
    )

    with pytest.raises(ValueError, match=re.escape("is not declared in [roots]")):
        load_records(manifest)


@pytest.mark.parametrize("triple", ["start", "final"], ids=["start", "final"])
@pytest.mark.parametrize("dropped", ["psnr", "ssim", "lpips"])
def test_a_run_record_missing_a_metric_is_refused(triple, dropped):
    """Parametrised over both triples and all three metrics because the check is
    a loop over the two and a set difference over the three — testing one cell of
    that grid would leave the loop and the difference unexercised, and the loop
    is where a future edit drops a triple."""
    complete = {
        "psnr": Measurement(20.0),
        "ssim": Measurement(0.9),
        "lpips": Measurement(0.1),
    }
    triples = {"start": dict(complete), "final": dict(complete)}
    del triples[triple][dropped]

    with pytest.raises(ValueError, match=f"{triple} triple is missing"):
        RunRecord(
            key="incomplete",
            start=triples["start"],
            final=triples["final"],
            num_primitives=1,
            eval_step=501,
            source="fixture://incomplete",
            provenance="a record with a hole in it",
        )


def test_the_message_names_the_metric_that_is_missing():
    """The guard above proves it fires; this proves the message is useful. Two
    assertions rather than one because "raises on a missing metric" and "says
    which" are different properties and only the second helps anyone."""
    with pytest.raises(ValueError, match=r"\['ssim'\]"):
        RunRecord(
            key="incomplete",
            start={"psnr": Measurement(20.0), "lpips": Measurement(0.1)},
            final={
                "psnr": Measurement(20.0),
                "ssim": Measurement(0.9),
                "lpips": Measurement(0.1),
            },
            num_primitives=1,
            eval_step=501,
            source="fixture://incomplete",
            provenance="a record with a hole in it",
        )


# ── the vendored-file requirement ───────────────────────────────────────────
def test_a_vendored_file_that_is_absent_raises_rather_than_skipping(tmp_path):
    """The reason is in the source at length and it is the reason this repository
    exists: a skip subtracts from the total and leaves the summary line green, so
    80 tests once vanished without the output saying so. This turns that into a
    collection error naming the file."""
    missing = tmp_path / "not-here.md"

    with pytest.raises(FileNotFoundError, match="This is a bug, not a reason to skip"):
        require_vendored(missing, "a document that is not there")


def test_a_vendored_file_that_is_present_is_returned_unchanged():
    """The control. A `require_vendored` that raised unconditionally would pass
    the test above."""
    present = EVIDENCE_ROOT / "PROVENANCE.toml"
    assert require_vendored(present, "the record itself") == present


def test_loading_the_record_from_a_directory_without_one_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no vendored-evidence record at"):
        load_evidence(tmp_path)


# ── display_path ────────────────────────────────────────────────────────────
def test_an_absolute_path_inside_the_repository_prints_relative_to_it():
    assert display_path(REPO_ROOT / "evidence" / "PROVENANCE.toml") == (
        "evidence/PROVENANCE.toml"
    )


@pytest.mark.parametrize(
    "given",
    ["fixture://manifest", "manifests/plan1.toml", "a sentinel, not a location"],
    ids=["scheme", "already-relative", "prose"],
)
def test_a_path_that_is_not_absolute_is_returned_as_written(given):
    """Resolving one against the working directory would make the rendered table
    depend on where the command was run from — which is the exact bug
    `display_path` exists to prevent, arrived at from the other side.

    **This pins the property, not the early return that implements it**, and the
    difference was found by deleting that return and watching the test stay
    green. `Path(relative).relative_to(REPO_ROOT)` raises `ValueError` against an
    absolute root, so the `except` clause hands back the same string the early
    return would have; the guard is belt-and-braces rather than load-bearing.
    Recorded rather than quietly relied upon, because a test whose subject turns
    out to be unobservable is the shape this repository has shipped before and
    now looks for.
    """
    assert display_path(given) == given


def test_an_absolute_path_outside_the_repository_is_returned_unchanged(tmp_path):
    """Not rendered politely: a path outside the repository is a bug at the call
    site, and the renderer's own guard is what catches it. Rewriting it here
    would hide the thing that needs to be seen."""
    outside = tmp_path / "somewhere-else.toml"
    assert display_path(outside) == str(outside)
