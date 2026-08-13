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
    COMMITTED_TREX_TABLE,
    DEFAULT_MANIFEST,
    PUBLISHED,
    TREX_MANIFEST,
    TREX_VENDORED_ARTEFACTS,
    ProvenanceError,
    collect_provenance,
    render_table,
)
from audit import forbidden_references  # noqa: E402
from plan1.assemble import assemble  # noqa: E402
from plan1.manifest import load_manifest, load_records  # noqa: E402

# `_HEADS` is the column head the published table prints per metric. The README's
# rows are keyed against it rather than against a second copy of "PSNR", so the two
# surfaces cannot come to disagree about what a column is called.
from plan1.render import _HEADS, format_fraction, format_measurement  # noqa: E402


@pytest.mark.parametrize(
    "manifest,committed",
    [
        pytest.param(DEFAULT_MANIFEST, COMMITTED_TABLE, id="penguin"),
        pytest.param(TREX_MANIFEST, COMMITTED_TREX_TABLE, id="trex"),
    ],
)
def test_the_committed_table_regenerates_byte_identically(manifest, committed):
    """The acceptance criterion, as a check that runs — now for both assets.

    The penguin's case is the one that guards the *second* asset's arrival rather
    than the second asset itself. Publishing trex moved the byline's
    pre-registration and the caption's limitations out of the renderer and into the
    manifest, and both of those changes ran through the code path the penguin table
    is built by. A change that quietly rewrote the first table while adding the
    second is exactly the failure this pair catches.
    """
    assert render_table(manifest) == committed.read_text()


def test_every_published_manifest_has_a_committed_table_and_its_own_footer_labels():
    """The registry is what the script, the gate and these tests all read.

    Asserted rather than trusted because it is the one place a third asset would
    have to be declared, and a manifest that reached `render_table` without an
    entry would otherwise print another comparison's footer reasons.
    """
    assert set(PUBLISHED) == {DEFAULT_MANIFEST, TREX_MANIFEST}
    for manifest, (committed, vendored) in PUBLISHED.items():
        assert manifest.is_file(), manifest
        assert committed.is_file(), committed
        assert vendored, manifest


def test_an_unpublished_manifest_is_refused_rather_than_given_a_default_footer(tmp_path):
    """The refusal, watched.

    Defaulting would print the penguin's reasons under a table that has no ρ = 32
    or ρ = 64 rows for them to be about — plausible-looking, silent, and wrong in
    the direction a reader cannot check.
    """
    with pytest.raises(ProvenanceError, match="not a published manifest"):
        render_table(tmp_path / "some_other.toml")


def test_the_two_tables_cite_the_same_artefacts_for_different_reasons():
    """Same three hashes, and one of the three labels deliberately differs.

    The paths must match — they are the same evidence — and the ρ = 32/64 label
    must **not** travel to a table whose sweep saturated at ρ = 4. A footer row
    naming rows the table does not contain is the plausible wrongness this
    repository refuses everywhere else.
    """
    from scripts.build_table import VENDORED_ARTEFACTS

    assert [path for _, path in VENDORED_ARTEFACTS] == [
        path for _, path in TREX_VENDORED_ARTEFACTS
    ]
    penguin_labels = [name for name, _ in VENDORED_ARTEFACTS]
    trex_labels = [name for name, _ in TREX_VENDORED_ARTEFACTS]
    assert penguin_labels != trex_labels
    assert any("ρ = 32/64" in name for name in penguin_labels)
    assert not any("32/64" in name for name in trex_labels)
    assert not any("32/64" in line for line in COMMITTED_TREX_TABLE.read_text().splitlines())


#: Both published manifests, for the guards that are properties of *any* table this
#: repository publishes rather than of one asset's numbers.
PUBLISHED_MANIFESTS = [
    pytest.param(DEFAULT_MANIFEST, id="penguin"),
    pytest.param(TREX_MANIFEST, id="trex"),
]


@pytest.mark.parametrize("manifest", PUBLISHED_MANIFESTS)
def test_the_rendered_table_names_no_absolute_path(manifest):
    """Byte-identity on this machine is not byte-identity on an examiner's.

    Every path the table prints — the manifest, each run record, each vendored
    source — has to be relative to the repository, or the output is a function of
    where the clone happens to sit.

    The home-directory half of this is delegated to `tests/audit.py` rather than
    spelled out here, so that "names a directory on somebody's computer" has one
    definition in this repository instead of one per guard. Spelling it out locally
    is how the manifest accumulated 55 of them while a Python-only guard watched.

    The trex table is the case that made this worth parametrising: its caption is
    prose declared in a manifest, and a manifest is exactly where 55 home paths
    once accumulated. Anything a manifest can put into a published table has to
    pass the same audit as anything the renderer writes.
    """
    absolute = [
        line
        for line in render_table(manifest).splitlines()
        if re.search(r"[`( ]/[A-Za-z]", line) or forbidden_references(line)
    ]
    assert not absolute, absolute


@pytest.mark.parametrize("manifest", PUBLISHED_MANIFESTS)
def test_the_rendered_table_resolves_nothing_outside_the_repository(manifest):
    """The point of the vendoring: no `3D`, no sibling archive, no `..`."""
    text = render_table(manifest)
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


@pytest.mark.parametrize(
    "manifest,expected",
    [
        pytest.param(
            DEFAULT_MANIFEST, "evidence/record/plan1_prereg.md", id="penguin"
        ),
        pytest.param(
            TREX_MANIFEST, "evidence/record/trex_comparison_prereg.md", id="trex"
        ),
    ],
)
def test_each_table_cites_the_pre_registration_that_actually_governs_it(
    manifest, expected
):
    """Two assets, two pre-registrations, and the byline has to know which is which.

    The byline used to name `plan1_prereg.md` for whatever it was rendering, which
    was correct while there was one table and became a mis-citation the moment
    there were two: trex's band, its baseline gate values, its branches and its
    prediction are declared in its own document, which *binds to* the penguin's for
    the rules it inherits. A reader sent to the wrong one finds a table's rules
    genuinely absent from the file the table names — the same defect as a citation
    that resolves nowhere, one step subtler, because this one resolves.

    Both halves are asserted: the byline says it, and the document is there to be
    read. A byline naming a file this repository does not ship would be exactly the
    uncheckable citation `README.md` argues against.
    """
    assert f"Rules pre-registered in `{expected}`." in render_table(manifest)
    assert (REPO / expected).is_file(), expected


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


# ── the front page, bound to the assembly ───────────────────────────────────
README = REPO / "README.md"


def readme_absolute_values(head: str = "metric") -> tuple[list[str], dict[str, list[str]]]:
    """`README.md`'s absolute-value table, as its header cells and its rows.

    Located by its first column head rather than by line number, so editing the
    prose around it cannot quietly point this at nothing — and asserted to be the
    only table of that shape, so a second one cannot be added and left unchecked.

    `head` is which of the two tables to read. The second asset's is headed `trex
    metric` rather than `metric` precisely so that "exactly one table of this shape"
    stays a real property of each rather than becoming a count that has to grow
    every time a table lands.
    """

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    lines = README.read_text().splitlines()
    heads = [index for index, line in enumerate(lines) if line.startswith(f"| {head} |")]
    assert len(heads) == 1, (
        f"expected exactly one table in README.md whose first column is `{head}`; "
        f"found {len(heads)}"
    )

    rows: dict[str, list[str]] = {}
    for line in lines[heads[0] + 2 :]:  # + 2 skips the alignment row
        if not line.startswith("|"):
            break
        cell = cells(line)
        rows[cell[0]] = cell[1:]
    return cells(lines[heads[0]]), rows


@pytest.mark.parametrize(
    "manifest,head",
    [
        pytest.param(DEFAULT_MANIFEST, "metric", id="penguin"),
        pytest.param(TREX_MANIFEST, "trex metric", id="trex"),
    ],
)
def test_the_readme_publishes_the_absolute_values_each_assembler_run_produces(
    manifest, head
):
    """The same binding as below, for both assets, in one walk.

    The second table arrived on the front page carrying its own three percentages
    and its own six endpoints. Nine more numbers typed where a reader lands is nine
    more that can go stale — and this repository's front page has gone stale three
    times on counts alone. So the trex cells are asserted against the trex assembly
    exactly as the penguin's are against the penguin's, through the same formatters
    the published tables print with, and the column heads are checked too: if the
    pre-registered rule ever selected a different rigidity, the middle head fails
    here rather than quietly describing the wrong row.
    """
    assembled = assemble(
        load_manifest(manifest), load_records(load_manifest(manifest))
    )
    selected = assembled.selected_row
    assert selected is not None and selected.fractions is not None

    header, published = readme_absolute_values(head)
    assert header == [
        head,
        assembled.row("vanilla").label,
        selected.label,
        assembled.row("baseline").label,
        "gap closed",
    ], header

    for metric, column in _HEADS.items():
        assert column in published, f"README.md publishes no row for {column}"
        assert published[column] == [
            format_measurement(assembled.row("vanilla").metrics[metric], metric),
            format_measurement(selected.metrics[metric], metric),
            format_measurement(assembled.row("baseline").metrics[metric], metric),
            format_fraction(selected.fractions[metric]),
        ], column


def test_the_readme_publishes_the_absolute_values_the_assembler_produces():
    """The percentages are the front page's claim; these are what they are of.

    `README.md` is what GitHub renders when the repository is opened, and it
    published `63.6% / 72.6% / 80.4%` with no absolute metric value anywhere in it.
    A reader who wanted to know what was recovered, and from what, had to find
    `out/comparison_table.md` and read the endpoints out themselves.

    A fraction quoted without its endpoints is the transcription risk this
    repository refuses everywhere else, one level up: three percentages typed into
    a second document, free to stay there while the runs behind them move. So the
    front page's cells are asserted against the **assembly** rather than against a
    copy of the rendered table — same manifest, same records, and the same
    formatters the published table prints through, so the front page cannot show a
    digit its source does not have either.

    Both the heads and the cells are checked. The heads are the assembled table's
    own row labels, so the README cannot carry the right numbers under the wrong
    description — and if the pre-registered rule ever selects a different rigidity,
    the middle column's head fails here rather than going stale.
    """
    manifest = load_manifest(DEFAULT_MANIFEST)
    assembled = assemble(manifest, load_records(manifest))
    selected = assembled.selected_row
    assert selected is not None and selected.fractions is not None, (
        "the rule published no row, so there is nothing for the README to quote"
    )

    header, published = readme_absolute_values()
    assert header == [
        "metric",
        assembled.row("vanilla").label,
        selected.label,
        assembled.row("baseline").label,
        "gap closed",
    ], header

    for metric, head in _HEADS.items():
        assert head in published, f"README.md publishes no row for {head}"
        assert published[head] == [
            format_measurement(assembled.row("vanilla").metrics[metric], metric),
            format_measurement(selected.metrics[metric], metric),
            format_measurement(assembled.row("baseline").metrics[metric], metric),
            format_fraction(selected.fractions[metric]),
        ], head


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


def test_the_trex_footer_names_the_same_three_and_says_why_they_are_its_evidence():
    """The trex table's own footer, held to the same shape and a different third row.

    The three identities are the same content; the reason the third is cited is
    not. Its sweep saturated at ρ = 4, so there is no ρ = 32 or ρ = 64 row for the
    patched call site to be the call site of — what it is evidence for here is the
    baseline row, whose console echoes this hash among its six.
    """
    footer = collect_provenance(vendored=TREX_VENDORED_ARTEFACTS)
    assert list(footer) == [
        "reference rule (`box_b/edge_weights.py`)",
        "deployed rule (`cluster/sources_20260729/helper.py`)",
        "patched call site, echoed by the baseline row's console "
        "(`cluster/sources_20260805_patched/deform_splat.py`)",
    ]
    for value in footer.values():
        assert value.startswith("sha256 "), value
