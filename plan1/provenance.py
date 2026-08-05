"""provenance.py — identifying the code that justified a published table.

Two questions have to stay answerable after the fact: *which version of the
reference rule did the conformance test bind to*, and *is the cluster source still
the one that produced the archived runs*. Both are answered by content, not by a
path or a timestamp.

Git state is read by **opening files under ``.git`` directly**, never by shelling
out to ``git``. The content hash is the primary identifier in any case — it stays
meaningful for the cluster sources, which are not in any repository.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


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
