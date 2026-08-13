#!/usr/bin/env python3
"""Regenerate a comparison table from its manifest.

    python scripts/build_table.py [manifest.toml] [-o out.md]

Adding a run is a manifest edit; no number is ever retyped. The script only reads
the manifest, drives the assembler, and prints — every decision lives behind the
seam in `plan1.assemble`.

**The footer is provenance, so a missing input is a failure.** This script used to
resolve four artefacts with `if path.is_file():` and drop the line when one was
absent. On a machine without the sibling checkouts that produced a table which
regenerated, looked right, and was missing two rows of the evidence that justified
it. Every input is now required, and one that has moved on from the identity
recorded in `evidence/PROVENANCE.toml` is an error naming both values.

**There are two tables, and the footer label differs between them.** Both cite the
same three artefacts by content, but *why* the third is cited is not the same fact:
on the penguin it is the call site the ρ = 32 and ρ = 64 rows went through, and the
trex table has no such rows. A footer row referring to rows that are not in the
table above it is the kind of plausible-looking wrongness this repository exists to
refuse, so the labels are declared per table rather than shared.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from plan1.assemble import AssemblyError, assemble  # noqa: E402
from plan1.manifest import load_manifest, load_records  # noqa: E402
from plan1.provenance import (  # noqa: E402
    EvidenceRecord,
    display_path,
    load_evidence,
    sha256_file,
)
from plan1.render import render_markdown  # noqa: E402

DEFAULT_MANIFEST = REPO / "manifests" / "penguin_deformsplat.toml"
COMMITTED_TABLE = REPO / "out" / "comparison_table.md"

TREX_MANIFEST = REPO / "manifests" / "trex_deformsplat.toml"
COMMITTED_TREX_TABLE = REPO / "out" / "trex_comparison_table.md"

#: The tested reference rule the conformance suite drives the deployed one
#: against. It used to be resolved from a sibling checkout outside this repository,
#: which is why this table regenerated differently — or not at all — on any
#: machine that did not have one. It is now a file in this repository, checked
#: against the identity the published table was assembled with. Nothing here
#: resolves `..` any more.
REFERENCE_RULE = REPO / "box_b" / "edge_weights.py"

#: The two archived cluster sources, now vendored. The manifest cites the second
#: hash as provenance for the rho = 32/64 rows, so publishing it beside the table
#: is what makes that citation checkable without cluster access.
VENDORED_ARTEFACTS = (
    (
        "deployed rule (`cluster/sources_20260729/helper.py`)",
        "cluster/sources_20260729/helper.py",
    ),
    (
        "patched call site, ρ = 32/64 rows "
        "(`cluster/sources_20260805_patched/deform_splat.py`)",
        "cluster/sources_20260805_patched/deform_splat.py",
    ),
)

#: The same three artefacts, cited by the trex table for a different second reason.
#: Its sweep saturated at ρ = 4, so it has no ρ = 32 or ρ = 64 rows for the patched
#: call site to be the call site *of* — carrying the penguin's label across would
#: annotate the footer with rows the table does not contain. What the patched source
#: is evidence for here is the **baseline** row, whose console echoes this hash among
#: its six. The manifest argues why that could not have touched the run: the patch is
#: wholly inside `if getattr(self.cfg, 'rho_enabled', False):`, only the sweep wrapper
#: sets that flag, and step 0 is evaluated upstream of the block in any case.
TREX_VENDORED_ARTEFACTS = (
    (
        "deployed rule (`cluster/sources_20260729/helper.py`)",
        "cluster/sources_20260729/helper.py",
    ),
    (
        "patched call site, echoed by the baseline row's console "
        "(`cluster/sources_20260805_patched/deform_splat.py`)",
        "cluster/sources_20260805_patched/deform_splat.py",
    ),
)

#: Which committed table each manifest publishes, and which footer labels it prints.
#: One place, so the script, the gate and the tests cannot come to disagree about
#: what is published from what.
PUBLISHED = {
    DEFAULT_MANIFEST: (COMMITTED_TABLE, VENDORED_ARTEFACTS),
    TREX_MANIFEST: (COMMITTED_TREX_TABLE, TREX_VENDORED_ARTEFACTS),
}


class ProvenanceError(Exception):
    """An artefact the table cites is missing, or is not the one it was built on."""


def collect_provenance(
    evidence: EvidenceRecord | None = None,
    reference_rule: Path = REFERENCE_RULE,
    vendored: tuple[tuple[str, str], ...] = VENDORED_ARTEFACTS,
) -> dict[str, str]:
    """Identify the code that justified the numbers, by content.

    `vendored` is the (label, path) pairs this table's footer cites. The paths are
    the same for both tables and the labels are not: a label says why the artefact
    is evidence *for this table*, and that reason is asset-specific.

    Raises
    ------
    ProvenanceError
        An input is absent, or its identity differs from the one recorded in
        `evidence/PROVENANCE.toml`. Never returns a partial footer.
    """
    evidence = load_evidence() if evidence is None else evidence
    found: dict[str, str] = {}

    reference = evidence.artefact("reference rule (`box_b/edge_weights.py`)")
    reference_path = Path(reference_rule)
    if not reference_path.is_file():
        raise ProvenanceError(
            f"{reference.name} is not present at {reference_path}. The published "
            f"table cites sha256 {reference.value}; evidence/PROVENANCE.toml "
            f"records it as {reference.origin}."
        )
    actual = sha256_file(reference_path)
    if actual != reference.value:
        raise ProvenanceError(
            f"{reference.name} at {reference_path} hashes to {actual}, which does "
            f"not match the recorded {reference.value}. The table was assembled "
            f"against the recorded version."
        )
    found[reference.name] = f"sha256 {reference.value[:16]}…"

    # A fourth row used to print here: the HEAD commit of the repository the method
    # was copied from, read out of the record. Before that it was read live off a
    # sibling checkout's `.git`, which made the footer a function of what else was
    # on the disk. Both are gone. The commit named a repository no reader can clone,
    # so the footer published a 40-hex identifier that could not be resolved and
    # could not be checked — decoration in the one table where every line is
    # supposed to be verifiable. The hash checked immediately above is what pins the
    # content, and it always was.

    for name, relative in vendored:
        path = evidence.resolve(relative)
        if not path.is_file():
            raise ProvenanceError(f"{name} is not present at {path}")
        found[name] = f"sha256 {sha256_file(path)[:16]}…"

    return found


def render_table(
    manifest_path: Path = DEFAULT_MANIFEST, *, reference_rule: Path = REFERENCE_RULE
) -> str:
    """The published table, as text. Deterministic: same inputs, same bytes."""
    manifest_path = Path(manifest_path).resolve()
    if manifest_path not in PUBLISHED:
        # Refused rather than defaulted. Falling back to one table's labels would
        # print a footer whose reasons belong to a different comparison, which is
        # exactly the plausible-looking wrongness the per-table labels exist to
        # stop — and it would do it silently, on a manifest nobody had reviewed.
        raise ProvenanceError(
            f"{display_path(manifest_path)} is not a published manifest. Every "
            f"table's footer cites its artefacts with reasons specific to that "
            f"comparison, so a new manifest needs an entry in PUBLISHED naming "
            f"its committed table and its footer labels. Declared: "
            f"{[display_path(p) for p in PUBLISHED]}"
        )
    _, vendored = PUBLISHED[manifest_path]
    manifest = load_manifest(manifest_path)
    table = assemble(manifest, load_records(manifest))
    return render_markdown(
        table,
        provenance=collect_provenance(
            reference_rule=reference_rule, vendored=vendored
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("-o", "--out", type=Path, help="write here instead of stdout")
    args = parser.parse_args(argv)

    try:
        text = render_table(args.manifest)
    except (AssemblyError, ProvenanceError, FileNotFoundError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
