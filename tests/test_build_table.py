"""Does the published table actually regenerate?

`out/comparison_table.md` is a committed output. The claim it carries is that a
reader can rebuild it from the manifest and the evidence in this repository and
get the same bytes. Until now that claim was untested, and it was false in three
independent ways at once: the header stamped `date.today()`, every provenance path
was absolute under one person's home directory, and `collect_provenance()` dropped
a footer line rather than failing when an input was missing.

None of those would have shown up as a failure. The table would regenerate, look
right, and differ.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

from scripts.build_table import (  # noqa: E402
    COMMITTED_TABLE,
    ProvenanceError,
    collect_provenance,
    render_table,
)
from audit import forbidden_references  # noqa: E402


def test_the_committed_table_regenerates_byte_identically():
    """The acceptance criterion, as a check that runs."""
    assert render_table() == COMMITTED_TABLE.read_text()


def test_the_rendered_table_names_no_absolute_path():
    """Byte-identity on this machine is not byte-identity on an examiner's.

    Every path the table prints — the manifest, each run record, each vendored
    source — has to be relative to the repository, or the output is a function of
    where the clone happens to sit.

    The home-directory half of this is delegated to `tests/audit.py` rather than
    spelled out here, so that "names a directory on somebody's computer" has one
    definition in this repository instead of one per guard. Spelling it out locally
    is how the manifest accumulated 55 of them while a Python-only guard watched.
    """
    absolute = [
        line
        for line in render_table().splitlines()
        if re.search(r"[`( ]/[A-Za-z]", line) or forbidden_references(line)
    ]
    assert not absolute, absolute


def test_the_rendered_table_resolves_nothing_outside_the_repository():
    """The point of the vendoring: no `3D`, no sibling archive, no `..`."""
    text = render_table()
    assert "3D/" not in text
    assert "../" not in text


def test_the_assembly_date_is_declared_rather_than_stamped_at_run_time():
    """`date.today()` made byte-identity true only on the day of publication.

    The date is a fact about the artefact, so it is declared in the manifest and
    travels with the rows it describes.
    """
    from plan1.manifest import load_manifest

    manifest = load_manifest(REPO / "manifests" / "penguin_deformsplat.toml")
    assert manifest.assembled == "2026-08-06"
    assert f"Assembled {manifest.assembled}" in render_table()


# ── a missing provenance input is loud ──────────────────────────────────────
def test_a_missing_provenance_input_raises_rather_than_dropping_a_line(tmp_path):
    """`if reference.is_file():` is why a bare clone regenerated a *different*
    table and reported success. The footer is provenance; a provenance table that
    silently omits a row is worse than no footer at all."""
    with pytest.raises(ProvenanceError, match="not present"):
        collect_provenance(reference_rule=tmp_path / "no-such-file.py")


def test_an_edited_reference_rule_raises_rather_than_publishing_a_new_hash(tmp_path):
    """The reference rule is in this repository, so it cannot *move* any more — but
    it can be edited, and an edited rule is a different rule. The check is the same
    one it always was, now pointed at a file this repository owns: identity is
    recorded, and content that has moved on is an error naming both values rather
    than a footer that quietly changed.
    """
    edited = tmp_path / "edge_weights.py"
    edited.write_text("# not the reference rule\n")

    with pytest.raises(ProvenanceError, match="does not match the recorded"):
        collect_provenance(reference_rule=edited)


def test_the_footer_names_every_recorded_artefact():
    """No row may be dropped, so the footer's shape is asserted rather than
    trusted to whichever inputs happened to resolve.

    Three rows, not the four this used to assert. The fourth printed the HEAD commit
    of the repository the method was copied from — an identifier in a repository no
    reader can clone, published in the one table where every line is supposed to be
    checkable. Each of the three that remain identifies content that is present
    here, so the footer can be verified with nothing but the clone.
    """
    footer = collect_provenance()
    assert list(footer) == [
        "reference rule (`box_b/edge_weights.py`)",
        "deployed rule (`cluster/sources_20260729/helper.py`)",
        "patched call site, ρ = 32/64 rows (`cluster/sources_20260805_patched/deform_splat.py`)",
    ]
    for value in footer.values():
        assert value.startswith("sha256 "), value
