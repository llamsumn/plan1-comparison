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


def head_commit(repo_dir: Path) -> str | None:
    """The commit ``HEAD`` points at, read straight off the filesystem.

    Returns ``None`` when ``repo_dir`` is not a git checkout or the ref cannot be
    resolved — an unidentifiable version is reported as unknown, never guessed.
    """
    git = Path(repo_dir) / ".git"
    if not git.is_dir():
        return None

    head_file = git / "HEAD"
    if not head_file.is_file():
        return None
    head = head_file.read_text().strip()

    if not head.startswith("ref: "):
        return head or None  # detached HEAD holds the sha directly

    ref = head[len("ref: ") :].strip()

    loose = git / ref
    if loose.is_file():
        return loose.read_text().strip() or None

    packed = git / "packed-refs"
    if packed.is_file():
        for line in packed.read_text().splitlines():
            if not line.strip() or line.startswith(("#", "^")):
                continue
            sha, _, name = line.partition(" ")
            if name.strip() == ref:
                return sha.strip()
    return None


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
    """One copied file: where it came from, what it hashes to, why it travelled."""

    path: str
    source: str
    sha256: str
    why: str


@dataclass(frozen=True)
class RecordedArtefact:
    """An identity the published table cites but does not vendor.

    Currently the two that name the method repository. They are recorded rather
    than copied because porting that repository is separate work (#16); until it
    lands, the sibling checkout is resolved and checked against ``value``.
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

    def resolve(self, path: str) -> Path:
        """A recorded path, as a location under the evidence root."""
        return (self.root / path).resolve()

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
    )
