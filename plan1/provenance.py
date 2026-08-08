"""provenance.py — identifying the code and the evidence that justified a table.

Three questions have to stay answerable after the fact: *which version of the
reference rule did the conformance test bind to*, *is the cluster source still the
one that produced the archived runs*, and *is the vendored copy of the evidence
still the original's*. All three are answered by content, not by a path or a
timestamp.

Git state is read by **opening files under ``.git`` directly**, never by shelling
out to ``git``. The content hash is the primary identifier in any case — it stays
meaningful for the cluster sources, which are not in any repository.

The evidence base itself lives under ``evidence/`` and is described by
``evidence/PROVENANCE.toml``. Vendoring it is what took every external path out of
this repository's runtime graph; recording what every byte *is*, and what it hashes
to, is what keeps the copy auditable against an original.
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


# ``head_commit()`` lived here once. It read a *sibling working tree's* git state
# off the filesystem so the table's footer could print that tree's HEAD, and it was
# the last thing in this package that reached outside the repository for anything.
# Deleting the function is what makes its absence a fact rather than a claim: there
# is no longer any code here that could resolve a sibling. The footer row it fed is
# gone too — a commit in a repository a reader cannot clone is an identifier that
# cannot be checked. What pins the method now is the content hash on its
# ``[[ported]]`` row in ``evidence/PROVENANCE.toml``, which is the part that ever
# did any work.


def require_vendored(path: Path, what: str) -> Path:
    """Assert a vendored input is present, or raise naming it.

    Called at module scope by the three suites that read the evidence base. Each
    of them used to carry ``pytestmark = pytest.mark.skipif(not path.is_file())``
    instead, from the era when the evidence lived in a checkout outside this
    repository and its absence was the normal case. Since it was vendored that is
    no longer so: the file is in the repository, and its absence means the
    repository is broken.

    The distinction is the whole point of raising here. A skip subtracts from the total and
    leaves the summary line green, so the suite reports a smaller number that
    looks exactly like the larger one — 60 passed where 140 should have run, with
    nothing in the output saying so. Raising here turns that into a collection
    error naming the missing file, which is loud, immediate, and impossible to
    read as success.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"{what} is missing at {path}. This is a bug, not a reason to skip: "
            f"it is vendored into this repository and recorded in "
            f"evidence/PROVENANCE.toml. Restore it from the record rather than "
            f"running a suite that silently omits what depends on it."
        )
    return path


def display_path(path: Path | str) -> str:
    """A path as a published artefact should print it: relative to the repository.

    A table that prints an absolute path — some clone location under somebody's
    home directory, then ``plan1-comparison/evidence/…`` — regenerates
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
    """One copied file: what it is, what it hashes to, why it travelled.

    ``origin`` says what the thing is — which run and which evaluation step, which
    study step, which document — rather than which directory the copy was reached
    in. It used to be a ``source`` path on the authoring machine, and that was
    worth less than it looked: a reader cannot resolve it, and for 24 of the rows it
    was character-identical to the file's own location here once the private prefix
    came off, so the prefix was the only thing it carried. What makes the copy
    auditable is ``sha256``, and that has not changed.

    ``command``, ``generated`` and ``certified_by`` are the three extra facts a
    *derived* artefact needs and a raw run record does not. A ``val_step0501.json``
    came off the cluster and is its own evidence; a figure or a summary CSV is the
    output of a program, and without the program, the date it ran and the verdict
    that checked the result, a reader cannot tell whether the file still means what
    the chapter citing it says. They are optional because the nine run directories
    predate them and genuinely have no generating command — see
    ``tests/test_vendored_evidence.py``, which requires all three of everything
    under ``characterisation/``.

    ``upstream_repo``, ``upstream_commit``, ``upstream_licence`` and ``modification``
    are the four a **third-party** file needs and a file of this project's own does
    not. Two rows carry them: the DeformSplat sources under ``cluster/``, which are
    Apache-2.0 and both locally modified. The licence asks that modified files carry a
    notice saying so, and they cannot — every byte under ``evidence/`` is hash-pinned
    and two suites parse these two files by AST, so a header inserted into either
    would break the manifest citation and the wiring harness at once. The notice is
    therefore carried *beside* the file: here, in ``THIRD_PARTY.md``, and as the
    complete diff under ``third_party/``.
    """

    path: str
    origin: str
    sha256: str
    why: str
    command: str | None = None
    generated: str | None = None
    certified_by: str | None = None
    upstream_repo: str | None = None
    upstream_commit: str | None = None
    upstream_licence: str | None = None
    modification: str | None = None
    archive_commit: str | None = None
    archive_date: str | None = None
    archive_first_commit: str | None = None
    archive_first_date: str | None = None


@dataclass(frozen=True)
class PortedFile:
    """One file of the method: what it is, and what it hashes to.

    Distinct from ``VendoredFile`` because these are not *evidence* — they are
    executable code that lives at the repository root and is imported, not read.
    The two need different homes on disk and the same discipline about identity, so
    they carry the same fields: ``origin``, ``sha256``, ``why``.

    These rows used to carry ``source_repo`` and ``source_commit`` instead, naming
    one of two of this author's own repositories and a 40-hex commit in it. Neither
    is published, so the citation could not be followed — and there was nobody to
    attribute to in any case: the code is this project's own and this repository is
    now its only published home. What the rows are *for* is unaffected, because it
    was never the commit: they are integrity pins, and ``sha256`` is the pin.

    ``attribution`` is for the one row that is not code and not this project's to
    give: ``data/penguin_original.ply`` is a 3DGS export of a checkpoint trained on
    a third-party dataset, so ``origin`` says what the file is while leaving whom it
    is owed to unrecorded. One field, naming the dataset and its licence, closes
    that.
    """

    path: str
    origin: str
    sha256: str
    why: str
    attribution: str | None = None


@dataclass(frozen=True)
class RecordedArtefact:
    """An identity the published table's footer cites.

    One row names the method: the reference rule's content hash, satisfied from
    inside this repository by hashing the file at ``box_b/edge_weights.py``.
    ``origin`` says which content the hash is of.

    A second row used to sit beside it, printing the HEAD commit of the repository
    the method was copied from. It published a 40-hex identifier a reader could not
    resolve, so the footer cited something uncheckable in order to look thorough. It
    is gone; the hash is what pins the content.
    """

    name: str
    kind: str
    origin: str
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
                origin=entry["origin"],
                sha256=entry["sha256"],
                why=entry["why"],
                command=entry.get("command"),
                generated=entry.get("generated"),
                certified_by=entry.get("certified_by"),
                upstream_repo=entry.get("upstream_repo"),
                upstream_commit=entry.get("upstream_commit"),
                upstream_licence=entry.get("upstream_licence"),
                modification=entry.get("modification"),
                archive_commit=entry.get("archive_commit"),
                archive_date=entry.get("archive_date"),
                archive_first_commit=entry.get("archive_first_commit"),
                archive_first_date=entry.get("archive_first_date"),
            )
            for entry in blob.get("file", ())
        ),
        artefacts=tuple(
            RecordedArtefact(
                name=entry["name"],
                kind=entry["kind"],
                origin=entry["origin"],
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
                origin=entry["origin"],
                sha256=entry["sha256"],
                why=entry["why"],
                attribution=entry.get("attribution"),
            )
            for entry in blob.get("ported", ())
        ),
    )
