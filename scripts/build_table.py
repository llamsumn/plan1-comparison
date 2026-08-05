#!/usr/bin/env python3
"""Regenerate the comparison table from the manifest.

    python scripts/build_table.py [manifest.toml] [-o out.md]

Adding a run is a manifest edit; no number is ever retyped. The script only reads
the manifest, drives the assembler, and prints — every decision lives behind the
seam in `plan1.assemble`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from plan1.assemble import AssemblyError, assemble  # noqa: E402
from plan1.manifest import load_manifest, load_records  # noqa: E402
from plan1.provenance import head_commit, sha256_file  # noqa: E402
from plan1.render import render_markdown  # noqa: E402

DEFAULT_MANIFEST = REPO / "manifests" / "penguin_deformsplat.toml"
METHOD_REPO = REPO.parent / "arap-deform-3dgs"
CLUSTER_HELPER = REPO.parent / "3D" / "cluster" / "sources_20260729" / "helper.py"


def collect_provenance() -> dict[str, str]:
    """Identify the code that justified the numbers, by content."""
    found: dict[str, str] = {}
    reference = METHOD_REPO / "box_b" / "edge_weights.py"
    if reference.is_file():
        found["reference rule (`box_b/edge_weights.py`)"] = f"sha256 {sha256_file(reference)[:16]}…"
    commit = head_commit(METHOD_REPO)
    found["method repository HEAD"] = commit or "unknown (not a resolvable checkout)"
    if CLUSTER_HELPER.is_file():
        found["deployed rule (`cluster/sources_20260729/helper.py`)"] = (
            f"sha256 {sha256_file(CLUSTER_HELPER)[:16]}…"
        )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("-o", "--out", type=Path, help="write here instead of stdout")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    try:
        records = load_records(manifest)
        table = assemble(manifest, records)
    except (AssemblyError, FileNotFoundError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    text = render_markdown(table, provenance=collect_provenance())
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
