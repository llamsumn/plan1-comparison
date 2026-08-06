#!/usr/bin/env python3
"""Regenerate the comparison table from the manifest.

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
    head_commit,
    load_evidence,
    sha256_file,
)
from plan1.render import render_markdown  # noqa: E402

DEFAULT_MANIFEST = REPO / "manifests" / "penguin_deformsplat.toml"
COMMITTED_TABLE = REPO / "out" / "comparison_table.md"

#: The one input this repository does not yet own. `box_b/edge_weights.py` is the
#: tested reference rule the conformance suite drives the deployed one against;
#: porting it is #16. Until then it is resolved from the sibling checkout and
#: checked against the identity the published table was assembled with.
METHOD_REPO = REPO.parent / "arap-deform-3dgs"

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


class ProvenanceError(Exception):
    """An artefact the table cites is missing, or is not the one it was built on."""


def collect_provenance(
    evidence: EvidenceRecord | None = None, method_repo: Path = METHOD_REPO
) -> dict[str, str]:
    """Identify the code that justified the numbers, by content.

    Raises
    ------
    ProvenanceError
        An input is absent, or its identity differs from the one recorded in
        `evidence/PROVENANCE.toml`. Never returns a partial footer.
    """
    evidence = load_evidence() if evidence is None else evidence
    found: dict[str, str] = {}

    reference = evidence.artefact("reference rule (`box_b/edge_weights.py`)")
    reference_path = Path(method_repo) / "box_b" / "edge_weights.py"
    if not reference_path.is_file():
        raise ProvenanceError(
            f"{reference.name} is not present at {reference_path}. The published "
            f"table cites sha256 {reference.value}; it is recorded in "
            f"evidence/PROVENANCE.toml as coming from {reference.source}."
        )
    actual = sha256_file(reference_path)
    if actual != reference.value:
        raise ProvenanceError(
            f"{reference.name} at {reference_path} hashes to {actual}, which does "
            f"not match the recorded {reference.value}. The table was assembled "
            f"against the recorded version."
        )
    found[reference.name] = f"sha256 {reference.value[:16]}…"

    head = evidence.artefact("method repository HEAD")
    commit = head_commit(Path(method_repo))
    if commit is None:
        raise ProvenanceError(
            f"{head.name} is not present: {method_repo} is not a resolvable "
            f"checkout. The published table cites {head.value}."
        )
    if commit != head.value:
        raise ProvenanceError(
            f"{head.name} is {commit}, which does not match the recorded "
            f"{head.value}. The table was assembled against the recorded commit."
        )
    found[head.name] = commit

    for name, relative in VENDORED_ARTEFACTS:
        path = evidence.resolve(relative)
        if not path.is_file():
            raise ProvenanceError(f"{name} is not present at {path}")
        found[name] = f"sha256 {sha256_file(path)[:16]}…"

    return found


def render_table(
    manifest_path: Path = DEFAULT_MANIFEST, *, method_repo: Path = METHOD_REPO
) -> str:
    """The published table, as text. Deterministic: same inputs, same bytes."""
    manifest = load_manifest(manifest_path)
    table = assemble(manifest, load_records(manifest))
    return render_markdown(table, provenance=collect_provenance(method_repo=method_repo))


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
