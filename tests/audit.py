"""audit.py — one definition of "a file in this repository", and the audits over it.

Three checks want the same walk over the same files, and before this module there
were three walks. `test_ported_method.py` parsed every `*.py` under the root by AST;
`test_suite_shape.py` globbed `tests/**/test_*.py`; `test_build_table.py` searched a
rendered string. Each carried its own notion of what counts as a file here, and the
gap between them was not hypothetical: the AST guard was **Python only**, so 55
home-directory paths accumulated in a `.toml` file with nothing looking at it, and
four links to a private repository sat in the published evidence manifest 404ing for
every visitor.

So the walk lives here, once, and it asks **git** rather than a glob: a file this
repository ships is a file git tracks, or one it is not ignoring and would add. That
is also the only definition that cannot drift from what a reader receives.

Three audits are built on it:

- `forbidden_references` — text that names something a reader cannot reach: a home
  directory, one of this author's unpublished repositories, a ticket in a private
  tracker.
- `relative_links` and `unresolvable_links` — Markdown links, and which of them
  resolve. Used both over the documents this repository authors and over the
  vendored records, which are byte-exact and therefore worked *around* rather than
  edited.
- `pragma_reasons` — coverage pragmas and the reason written beside each one. Not
  asserted anywhere yet; it belongs to the coverage work and is built here because
  it is the same walk.

**The needles are assembled from parts, deliberately.** Every forbidden string
below is written as a concatenation, so this file does not contain the text it
hunts, and does not have to be exempted from its own audit. That matters more than
it looks: an exemption is one careless edit away from a guard that passes because it
stopped looking, and this repository has already shipped two guards that could not
fail. `test_source_audit.py` asserts that this module and its own test module are
audited like everything else.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from plan1.provenance import REPO_ROOT

# ── the needles ─────────────────────────────────────────────────────────────
#: Markers for a path on somebody's computer. A leading tilde-and-separator is how
#: the manifest recorded all 55 of its sources; the other two are how an absolute
#: path to a clone begins on the two platforms this is likely to be read on.
HOME_MARKERS = ("~" + "/", "/" + "Users" + "/", "/" + "home" + "/")

#: This author's repositories that are not published. A reference to one is a
#: citation a reader cannot follow — and for the two that carried ~2,000 ported
#: lines there is nobody to attribute to either, because the code is this project's
#: own and this repository is its only published home.
PRIVATE_REPOS = ("3D" + "-arap", "arap-deform" + "-3dgs", "github.com/" + "llamsumn")

#: A bare ticket reference: a hash followed by one to three digits. 27 of these
#: pointed into a tracker nobody outside the project can read.
#:
#: The trailing lookahead is what keeps hex colours out — a six-digit colour
#: literal has hex characters after its third digit, so it is not a ticket. The
#: leading one keeps out anything already part of a word or a comment marker.
#:
#: It catches the *notation* and not the habit. A sentence that points at a tracker
#: item in words, or names an internal label, is a reference a reader cannot follow
#: just as much, and no regex should be asked to chase it — that one is a review
#: matter, and the rule it answers to is in `CONTEXT.md`.
_TICKET = re.compile(r"(?<![\w#$&])#(\d{1,3})(?![\da-fA-F])")

#: A commit, in prose. Either seven-plus hex characters with a digit among them, or
#: twelve-plus without — because the plain "seven or more hex characters" reading
#: matches `defaced`, `effaced` and `acceded`, and a guard that fires on an English
#: word is a guard somebody switches off. Nothing shorter than twelve is all-letters
#: in practice, and no English word is twelve.
_COMMIT = re.compile(r"\b(?:(?=[0-9a-f]*\d)[0-9a-f]{7,40}|[0-9a-f]{12,40})\b")

#: Files under `evidence/` that this repository **authored** rather than copied.
#: Everything else there is a vendored byte-exact copy, which is why it is exempt
#: from the reference audit and why it carries a provenance row. These two are the
#: other way round: audited like any other source file, and no provenance row,
#: because there is no original to audit them against.
#:
#: Consumed by `test_vendored_evidence.py` as well, so "what needs a row" and "what
#: gets audited" cannot drift apart.
AUTHORED_UNDER_EVIDENCE = (
    "evidence/PROVENANCE.toml",
    "evidence/record/LINKS.md",
)

#: The reason the vendored tree is not read by the reference audit. Stated once,
#: reported by `exemption()`, so a reader meeting a skipped file gets the argument
#: rather than an absence.
VENDORED_EXEMPTION = (
    "vendored byte-exact and pinned by sha256 in evidence/PROVENANCE.toml. The "
    "copy is evidence only while it is unedited, so what it names cannot be "
    "cleaned — the cluster account's own paths are in the run logs on purpose. "
    "Links out of the two records are classified in evidence/record/LINKS.md "
    "instead, and tests/test_vendored_record_links.py enforces that."
)


@dataclass(frozen=True)
class Finding:
    """One forbidden reference, at the line that carries it."""

    line: int
    kind: str
    match: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.kind} {self.match!r}"


def forbidden_references(text: str) -> list[Finding]:
    """Every reference in `text` that a reader of this repository cannot follow.

    Reported per occurrence with a line number, because the useful failure names
    the line to edit rather than the file to go looking through.
    """
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for marker in HOME_MARKERS:
            if marker in line:
                findings.append(Finding(number, "home path", marker))
        for repository in PRIVATE_REPOS:
            if repository in line:
                findings.append(Finding(number, "private repository", repository))
        for match in _TICKET.finditer(line):
            findings.append(Finding(number, "ticket reference", match.group(0)))
    return findings


def origin_problems(origin: str) -> list[str]:
    """Why this manifest `origin` is not self-contained prose, if it is not.

    One definition for both row types. `[[file]]` rows and `[[ported]]` rows carry
    the same field and used to be guarded by two different assertions — one
    forbidding a path, the other a repository and a commit — so each row type was
    checked for half of what the property actually is. A path is no more resolvable
    on a ported row than on a vendored one.

    Returns the reasons rather than raising, so the two guards can name the row and
    a negative control can drive this directly.
    """
    problems = [str(finding) for finding in forbidden_references(origin)]
    if not origin.strip():
        problems.append("empty — a row that says nothing about what the file is")
    if "/" in origin:
        problems.append(
            "looks like a path — it should say what the file is (which run, which "
            "step, which document), not where a copy of it once sat"
        )
    commit = _COMMIT.search(origin)
    if commit:
        problems.append(
            f"names a commit ({commit.group(0)}) — an identifier in a repository a "
            f"reader cannot clone; the row's sha256 is what pins the content"
        )
    return problems


# ── the walk ────────────────────────────────────────────────────────────────
def repository_files() -> tuple[Path, ...]:
    """Every file this repository ships, or would ship, as absolute paths.

    Tracked files **and** untracked ones git is not ignoring — the second half is
    load-bearing rather than tidy. A new file is exactly when a private path gets
    written, and a walk over `--cached` alone cannot see one until the commit that
    adds it, so the audit would first run on the leak one commit after it was
    reviewable. Anything `.gitignore` covers is genuinely not part of the artefact
    and is skipped.

    Raises rather than returning nothing when git cannot answer. An empty list
    would make every audit built on this pass, loudly and vacuously — which is the
    precise failure shape this repository exists to be free of. `git` is already a
    hard requirement of the green gate: `scripts/verify.sh` diffs the regenerated
    table with it.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"`git ls-files` failed in {REPO_ROOT} (exit {result.returncode}): "
            f"{result.stderr.strip()!r}. Every audit over the repository's own "
            f"sources is built on this list, so an empty one would pass "
            f"vacuously. Run the suite in a git checkout."
        )
    paths = tuple(
        REPO_ROOT / name
        for name in result.stdout.split("\0")
        if name and (REPO_ROOT / name).is_file()
    )
    if not paths:
        raise RuntimeError(
            f"`git ls-files` reported no files in {REPO_ROOT}. The audits below "
            f"would pass vacuously, so this is an error rather than an empty "
            f"result."
        )
    return paths


def is_text(path: Path) -> bool:
    """Does this file hold text? Decided by content, not by extension.

    A NUL byte in the first block is the classic test and it is the right one here:
    the eleven binaries in this repository are PNGs, PDFs and two PLY files, and a
    PLY has an ASCII header over a binary body, so an extension list would have to
    know about that and a decode attempt alone would depend on where the body's
    bytes happened to fall.
    """
    with open(path, "rb") as handle:
        return b"\0" not in handle.read(8192)


def exemption(relative: str) -> str | None:
    """Why this file is not read by the reference audit, or `None` if it is.

    The only exempt files are the vendored copies: their bytes are the evidence, so
    editing them to remove a reference would destroy the thing they are here for.
    Everything this repository *wrote* is audited, including this module and its
    tests.
    """
    if relative.startswith("evidence/") and relative not in AUTHORED_UNDER_EVIDENCE:
        return VENDORED_EXEMPTION
    return None


def audited_files() -> tuple[Path, ...]:
    """The repository's text files that the reference audit reads."""
    return tuple(
        path
        for path in repository_files()
        if is_text(path) and exemption(str(path.relative_to(REPO_ROOT))) is None
    )


# ── Markdown links ──────────────────────────────────────────────────────────
#: An inline Markdown link. `DOTALL` because both vendored records wrap a link's
#: label across a line, and a pattern that stopped at the newline would report
#: nine of the fifteen links in them and call the rest absent.
_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)", re.DOTALL)

#: Link targets that are not paths into the repository and so are nothing to
#: resolve on disk.
_NOT_A_PATH = ("http://", "https://", "mailto:", "#")


@dataclass(frozen=True)
class RelativeLink:
    """One inline Markdown link, as written."""

    line: int
    label: str
    target: str

    def resolved_from(self, document: Path) -> Path:
        """Where the link points, read from the document that carries it."""
        return (document.parent / self.target).resolve()

    def resolves_from(self, document: Path) -> bool:
        return self.resolved_from(document).exists()

    def __str__(self) -> str:
        return f"line {self.line}: [{' '.join(self.label.split())}]({self.target})"


def relative_links(markdown: str) -> list[RelativeLink]:
    """Every inline link in `markdown` that points at a path rather than a URL."""
    links: list[RelativeLink] = []
    for match in _LINK.finditer(markdown):
        target = match.group(2)
        if target.startswith(_NOT_A_PATH):
            continue
        links.append(
            RelativeLink(
                line=markdown[: match.start()].count("\n") + 1,
                label=match.group(1),
                target=target,
            )
        )
    return links


def unresolvable_links(document: Path) -> list[RelativeLink]:
    """The links in `document` whose targets are not in this repository."""
    return [
        link
        for link in relative_links(document.read_text())
        if not link.resolves_from(document)
    ]


#: The two ways a dead link in a vendored record can be accounted for. A redirect
#: says the target is here under another path; an exclusion says the target is a
#: document that deliberately did not travel, and why.
LINK_KINDS = ("redirect", "exclusion")

#: A section heading, which is what says whether the table under it is classifying
#: redirects or exclusions.
_HEADING = re.compile(r"^##\s+(?P<title>.*)$")

#: A table row whose first cell is a single code span — the link target. Rows whose
#: first cell is anything else (a header, a rule) carry no classification.
_FIRST_CELL = re.compile(r"^\|\s*`(?P<target>[^`]+)`\s*\|")


def link_classifications(note: str) -> dict[str, str]:
    """Every link target the companion note accounts for, and how.

    The note is prose for a reader; this is the half a test can hold to. It reads
    the first column of the table under each classifying heading, so the document a
    person reads and the record a test enforces are the same document — a note kept
    in step by hand drifts, and a machine-readable file beside it is one more thing
    to keep in step.
    """
    found: dict[str, str] = {}
    kind: str | None = None
    for line in note.splitlines():
        heading = _HEADING.match(line)
        if heading:
            title = heading.group("title").lower()
            kind = next((k for k in LINK_KINDS if k in title or f"{k}s" in title), None)
            continue
        cell = _FIRST_CELL.match(line)
        if cell and kind is not None:
            found[cell.group("target")] = kind
    return found


# ── coverage pragmas ────────────────────────────────────────────────────────
#: A coverage pragma, and whatever was written after it as a reason.
_PRAGMA = re.compile(r"#\s*pragma:\s*no cover\b[\s\-—:]*(?P<reason>.*)")


@dataclass(frozen=True)
class PragmaReason:
    """One `no cover` pragma, and the reason beside it. Empty when there is none."""

    line: int
    reason: str


def pragma_reasons(python_source: str) -> list[PragmaReason]:
    """Every coverage pragma in `python_source`, with its stated reason.

    The reason is what makes an exclusion reviewable — "this line is not covered"
    is a fact, "this line cannot be reached without a corrupt PLY on disk" is an
    argument. Extracted here rather than asserted; the coverage work is what
    requires every pragma to carry one.
    """
    found: list[PragmaReason] = []
    for number, line in enumerate(python_source.splitlines(), start=1):
        match = _PRAGMA.search(line)
        if match:
            found.append(PragmaReason(number, match.group("reason").strip()))
    return found
