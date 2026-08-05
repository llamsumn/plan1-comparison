"""manifest.py — the version-controlled binding from table rows to source records.

Rows are bound to sources by an explicit manifest, never inferred from directory
names or from the numbers themselves. The concrete reason: two archived penguin
runs score within 0.0001 dB of each other, carry different roles in the table, and
are separable only on the secondary metrics. Any heuristic binding will eventually
swap them, and the resulting table would be wrong in a way that looks entirely
plausible.

The manifest also carries what information each arm had access to. That column is
the frame of the whole comparison — the baseline has *seen the object move* — so it
travels with the table rather than being left to prose.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from plan1.records import RunRecord, read_console_log, read_stats_json

#: The roles a row may carry. Exactly one ``baseline`` and one ``null`` are
#: required — they are the two endpoints the gap fraction is measured between.
ROLES: tuple[str, ...] = ("baseline", "null", "null_replicate", "imposed")

_KINDS = {"stats_json", "console_log"}


@dataclass(frozen=True)
class ManifestRow:
    """One declared row: its role in the table and where its numbers come from."""

    key: str
    label: str
    role: str
    rigidity: float | None
    information: str
    kind: str
    root: str
    path: str

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(
                f"row {self.key!r}: kind must be one of {sorted(_KINDS)}; "
                f"got {self.kind!r}"
            )


@dataclass(frozen=True)
class Manifest:
    asset: str
    eval_step: int
    rows: tuple[ManifestRow, ...]
    source: str
    roots: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        keys = [row.key for row in self.rows]
        duplicates = {k for k in keys if keys.count(k) > 1}
        if duplicates:
            raise ValueError(f"duplicate manifest keys: {sorted(duplicates)}")


def load_manifest(path: Path) -> Manifest:
    """Read a manifest TOML file. Paths inside it resolve against its own directory."""
    path = Path(path).resolve()
    blob = tomllib.loads(path.read_text())

    rows = tuple(
        ManifestRow(
            key=entry["key"],
            label=entry["label"],
            role=entry["role"],
            rigidity=float(entry["rigidity"]) if "rigidity" in entry else None,
            information=entry.get("information", "—"),
            kind=entry["kind"],
            root=entry["root"],
            path=entry["path"],
        )
        for entry in blob.get("row", ())
    )
    return Manifest(
        asset=blob["asset"],
        eval_step=int(blob["eval_step"]),
        rows=rows,
        source=str(path),
        roots=blob.get("roots", {}),
    )


def load_records(manifest: Manifest) -> dict[str, RunRecord]:
    """Read every record the manifest names. Reads only what the manifest names.

    Raises if a named record does not exist — a manifest that points at nothing is
    a broken table, not a table with a gap in it.
    """
    base = Path(manifest.source).parent
    records: dict[str, RunRecord] = {}
    for row in manifest.rows:
        if row.root not in manifest.roots:
            raise ValueError(
                f"row {row.key!r}: root {row.root!r} is not declared in [roots] "
                f"(declared: {sorted(manifest.roots)})"
            )
        location = (base / manifest.roots[row.root] / row.path).resolve()
        if row.kind == "stats_json":
            records[row.key] = read_stats_json(location, manifest.eval_step, row.key)
        else:
            records[row.key] = read_console_log(location, manifest.eval_step, row.key)
    return records
