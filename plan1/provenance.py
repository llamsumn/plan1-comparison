"""provenance.py — identifying the code and the evidence that justified a table.

Three questions have to stay answerable after the fact: *which version of the
reference rule did the conformance test bind to*, *is the cluster source still the
one that produced the archived runs*, and *is the vendored copy of the evidence
still the archive's*. All three are answered by content, not by a path or a
timestamp.

Git state is read by **opening files under ``.git`` directly**, never by shelling
out to ``git``. The content hash is the primary identifier in any case — it stays
meaningful for the cluster sources, which are not in any repository.

The evidence base itself lives under ``evidence/`` and is described by
``evidence/PROVENANCE.toml``. Vendoring it is what took ``~/3D`` out of this
repository's runtime graph; recording where every byte came from is what keeps the
copy auditable against an original.
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

#: The repository root, and the vendored evidence base beneath it. Everything this
#: repository reads at run time is under one of these two — there is no sibling to
#: resolve and no archive to find.
REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / "evidence"


def sha256_file(path: Path) -> str:
    """The SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


# ``head_commit()`` lived here until #16. It read a *sibling working tree's* git
# state off the filesystem so the table's footer could name the method repository's
# HEAD, and it was the last thing in this package that reached outside the
# repository for anything. The method is now vendored (see ``[[ported]]`` in
# ``evidence/PROVENANCE.toml``), so the commit it used to read is a recorded fact
# about where the copy came from rather than a live observation of a checkout that
# may not exist. Deleting the function is what makes that true rather than merely
# claimed: there is no longer any code here that could resolve a sibling.


def display_path(path: Path | str) -> str:
    """A path as a published artefact should print it: relative to the repository.

    A table that prints ``/Users/someone/plan1-comparison/evidence/…`` regenerates
    byte-identically on exactly one machine. Anything inside the repository is
    printed relative to it; anything outside is a bug at the call site rather than
    something to render politely, so it is returned unchanged and the renderer's
    own guard is what catches it.

    Only absolute paths are rewritten. Every real caller resolves its path before
    getting here, so a relative input is a fixture sentinel rather than a location
    — and resolving one against the working directory would make the output depend
    on where the command was run from, which is the bug this function exists for.
    """
    text = str(path)
    if not Path(text).is_absolute():
        return text
    try:
        return str(Path(text).relative_to(REPO_ROOT))
    except ValueError:
        return text


# ── the vendored evidence base ──────────────────────────────────────────────
@dataclass(frozen=True)
class VendoredFile:
    """One copied file: where it came from, what it hashes to, why it travelled.

    ``command``, ``generated`` and ``certified_by`` are the three extra facts a
    *derived* artefact needs and a raw run record does not. A ``val_step0501.json``
    came off the cluster and is its own evidence; a figure or a summary CSV is the
    output of a program, and without the program, the date it ran and the verdict
    that checked the result, a reader cannot tell whether the file still means what
    the chapter citing it says. They are optional because the nine run directories
    predate them and genuinely have no generating command — see
    ``tests/test_vendored_evidence.py``, which requires all three of everything
    under ``characterisation/``.
    """

    path: str
    source: str
    sha256: str
    why: str
    command: str | None = None
    generated: str | None = None
    certified_by: str | None = None


@dataclass(frozen=True)
class PortedFile:
    """One file copied out of the method repository, and where it came from.

    Distinct from ``VendoredFile`` because these are not *evidence* — they are
    executable code that lives at the repository root and is imported, not read.
    The two need different homes on disk and the same discipline about identity:
    source repository, source commit, and a hash.
    """

    path: str
    source_repo: str
    source_commit: str
    sha256: str
    why: str


@dataclass(frozen=True)
class RecordedArtefact:
    """An identity the published table's footer cites.

    The two that name the method: the reference rule's content hash, and the
    commit of the repository the vendored copy was taken from. Since #16 both are
    satisfied from inside this repository — the rule is hashed from the ported
    file, and the commit is read from this record. ``source`` therefore names
    where the copy *came from*, and is provenance rather than a location anything
    resolves.
    """

    name: str
    kind: str
    source: str
    value: str
    why: str


@dataclass(frozen=True)
class ExcludedPath:
    """Something the archive held that deliberately did not travel."""

    path: str
    size: str
    reason: str


@dataclass(frozen=True)
class EvidenceRecord:
    root: Path
    files: tuple[VendoredFile, ...]
    artefacts: tuple[RecordedArtefact, ...]
    excluded: tuple[ExcludedPath, ...]
    ported: tuple[PortedFile, ...] = ()

    def resolve(self, path: str) -> Path:
        """A recorded path, as a location under the evidence root."""
        return (self.root / path).resolve()

    def resolve_ported(self, path: str) -> Path:
        """A ported path, as a location under the repository root.

        Ported code is importable and so lives at the root, not under
        ``evidence/`` — ``arap_core/`` has to be ``arap_core``.
        """
        return (REPO_ROOT / path).resolve()

    def ported_file(self, path: str) -> PortedFile:
        for entry in self.ported:
            if entry.path == path:
                return entry
        raise KeyError(path)

    def artefact(self, name: str) -> RecordedArtefact:
        for artefact in self.artefacts:
            if artefact.name == name:
                return artefact
        raise KeyError(name)


def load_evidence(root: Path = EVIDENCE_ROOT) -> EvidenceRecord:
    """Read ``PROVENANCE.toml``. A malformed row raises rather than being skipped."""
    root = Path(root)
    record = root / "PROVENANCE.toml"
    if not record.is_file():
        raise FileNotFoundError(f"no vendored-evidence record at {record}")
    blob = tomllib.loads(record.read_text())
    return EvidenceRecord(
        root=root,
        files=tuple(
            VendoredFile(
                path=entry["path"],
                source=entry["source"],
                sha256=entry["sha256"],
                why=entry["why"],
                command=entry.get("command"),
                generated=entry.get("generated"),
                certified_by=entry.get("certified_by"),
            )
            for entry in blob.get("file", ())
        ),
        artefacts=tuple(
            RecordedArtefact(
                name=entry["name"],
                kind=entry["kind"],
                source=entry["source"],
                value=entry["value"],
                why=entry["why"],
            )
            for entry in blob.get("artefact", ())
        ),
        excluded=tuple(
            ExcludedPath(path=entry["path"], size=entry["size"], reason=entry["reason"])
            for entry in blob.get("excluded", ())
        ),
        ported=tuple(
            PortedFile(
                path=entry["path"],
                source_repo=entry["source_repo"],
                source_commit=entry["source_commit"],
                sha256=entry["sha256"],
                why=entry["why"],
            )
            for entry in blob.get("ported", ())
        ),
    )
