"""No file in this repository names something a reader cannot reach.

The repository already asserted a version of this and it was **Python only**: an
AST guard in `test_ported_method.py` that parsed every `*.py` for a string naming a
sibling working tree. It did its job, and the gap beside it did not stay
hypothetical. While it watched the modules, the published evidence manifest
accumulated

- 55 paths under a home directory on the authoring machine, one per vendored file,
- 4 links to a private repository — live 404s for every visitor, since this
  repository is public and that one is not, and
- 9 references to tickets in a tracker nobody outside the project can read,

in a `.toml` file, which the guard did not look at. Eighteen more ticket references
sat in the test modules, the packaging metadata, the ignore rules and the solver
diagnostic for the same reason — 27 in all.

So the audit is over **every tracked text file**, and the walk is git's answer
rather than a glob (`tests/audit.py`). The one exempt set is the vendored tree,
because those bytes *are* the evidence and editing them to clean up what they name
would destroy the property they are here for — `exemption()` states that argument
and `test_the_vendored_exemption_is_load_bearing` proves the exemption is not
decoration.

**Each detector is watched failing before it is trusted.** The three negative
controls below build a deliberately bad input out of `audit.py`'s own needles and
assert the detector fires. This repository has shipped two guards that could not
fail — an in-run assertion that evaluated `torch.equal(w, w)`, and a provenance
footer that dropped the rows it could not resolve — so a guard nobody has watched
fail is not treated as a guard here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from audit import (
    AUTHORED_UNDER_EVIDENCE,
    HOME_MARKERS,
    PRIVATE_REPOS,
    audited_files,
    exemption,
    forbidden_references,
    is_text,
    pragma_reasons,
    repository_files,
    unresolvable_links,
)
from plan1.provenance import REPO_ROOT

AUDITED = audited_files()

#: The audited files that carry Markdown links. Parametrised separately rather than
#: skipping 59 of 64 inside one test: a case that returns without asserting still
#: counts as a pass, and this repository asserts its own test total, so vacuous
#: parameters would inflate a number that is supposed to mean something.
AUDITED_MARKDOWN = tuple(path for path in AUDITED if path.suffix == ".md")


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


# ── the audit itself ────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", AUDITED, ids=_relative)
def test_no_tracked_file_names_anything_a_reader_cannot_reach(path):
    """One test per file, so a failure names the file and the line inside it."""
    findings = forbidden_references(path.read_text())
    assert not findings, (
        f"{_relative(path)} names things no reader of this repository can "
        f"resolve:\n  " + "\n  ".join(str(finding) for finding in findings)
    )


@pytest.mark.parametrize("path", AUDITED_MARKDOWN, ids=_relative)
def test_no_authored_document_links_to_something_that_is_not_here(path):
    """A citation that resolves nowhere is worse than none.

    That sentence is in `README.md`, and this is it applied to the documents this
    repository writes rather than only to the ones it vendors. The vendored records
    are byte-exact and cannot be edited, so their dead links are classified in
    `evidence/record/LINKS.md` and enforced by `test_vendored_record_links.py`
    instead.
    """
    dead = unresolvable_links(path)
    assert not dead, (
        f"{_relative(path)} links to paths that are not in this repository:\n  "
        + "\n  ".join(str(link) for link in dead)
    )


# ── the walk is not vacuous ─────────────────────────────────────────────────
def test_the_audit_reads_more_than_python():
    """The gap that let 55 private paths into a `.toml` file, closed as a property.

    Asserted on the file types actually present rather than on a count, because the
    count is not the point — the point is that the manifest, the packaging metadata
    and the ignore rules are audited alongside the modules.
    """
    suffixes = {path.suffix for path in AUDITED}
    for expected in (".py", ".toml", ".md", ".sh"):
        assert expected in suffixes, expected
    assert REPO_ROOT / "evidence" / "PROVENANCE.toml" in AUDITED
    assert REPO_ROOT / ".gitignore" in AUDITED


def test_the_file_list_is_the_whole_repository_not_a_corner_of_it():
    """`git ls-files` returning nothing would make every audit above pass.

    `repository_files()` raises in that case rather than returning an empty tuple,
    and this is the check that what it returns is a repository rather than a
    directory: eleven binaries, and text files in every tree that ships.
    """
    files = repository_files()
    assert len(files) > 100, len(files)
    binaries = [path for path in files if not is_text(path)]
    assert len(binaries) == 11, [_relative(path) for path in binaries]
    trees = {_relative(path).split("/")[0] for path in files}
    assert {"plan1", "tests", "scripts", "evidence", "arap_core", "box_b"} <= trees


def test_a_new_file_is_audited_before_it_is_committed_rather_than_after():
    """The walk covers untracked files git is not ignoring, and that is the point.

    A private path gets written when a file is *new*. A walk over tracked files
    alone would first see it one commit after the moment it was reviewable, which
    is the wrong side of the review. Asserted on the property rather than on a
    fixture: every file this test module needs in order to run is in the audited
    set, whether or not it has been committed yet.
    """
    for path in (
        REPO_ROOT / "tests" / "audit.py",
        REPO_ROOT / "tests" / "test_source_audit.py",
        REPO_ROOT / "evidence" / "record" / "LINKS.md",
    ):
        assert path in AUDITED, _relative(path)


def test_this_module_and_the_audit_it_uses_are_audited_like_everything_else():
    """No guard here is exempt from itself.

    `audit.py` writes every forbidden string as a concatenation so that it does not
    contain the text it hunts. That is what buys this: the two files that have to
    know the needles are audited by them, and an exemption that could rot into a
    guard which passes because it stopped looking never has to exist.
    """
    for path in (REPO_ROOT / "tests" / "audit.py", Path(__file__).resolve()):
        assert path in AUDITED, _relative(path)
        assert exemption(_relative(path)) is None


# ── negative controls: each detector must be able to fire ───────────────────
def test_the_audit_catches_a_home_directory_path():
    findings = forbidden_references(
        f'source = "{HOME_MARKERS[0]}3D/cluster/rho_probe_evidence/x.json"'
    )
    assert [finding.kind for finding in findings] == ["home path"]


def test_the_audit_catches_a_private_repository_name():
    findings = forbidden_references(f'source_repo = "{PRIVATE_REPOS[1]}"')
    assert [finding.kind for finding in findings] == ["private repository"]


def test_the_audit_catches_a_ticket_reference():
    findings = forbidden_references("# ported under " + "#" + "16, see the tracker")
    assert [finding.kind for finding in findings] == ["ticket reference"]
    assert findings[0].line == 1


@pytest.mark.parametrize(
    "innocent",
    [
        '    color="#444444"',  # a six-digit hex colour, not a ticket
        '    c="#1f4e79"',  # nor a mixed one
        "#!/usr/bin/env bash",
        "### A Markdown heading",
        "step 501 of the validation pass",
    ],
)
def test_the_ticket_detector_leaves_the_things_that_merely_look_like_one(innocent):
    """A detector that fired on a colour literal would be turned off within a week."""
    assert not forbidden_references(innocent)


def test_the_vendored_exemption_is_load_bearing():
    """An exemption for something that would not have failed anyway is decoration.

    The run logs carry the cluster account's username, hostname and home-directory
    paths, and `README.md` explains why they are left in: the file is pinned by
    sha256, and redacting it would break the hash that makes its 6/6 source-hash
    comparison checkable. So the exemption has real work to do, and this asserts it
    — if the vendored tree were clean, the right change would be to delete the
    exemption rather than to keep it.
    """
    exempt = [
        path
        for path in repository_files()
        if is_text(path) and exemption(_relative(path)) is not None
    ]
    assert exempt, "nothing is exempt, so the exemption should be deleted"
    offenders = {
        _relative(path)
        for path in exempt
        if forbidden_references(path.read_text())
    }
    assert offenders, (
        "no exempt file contains anything the audit would have caught, so the "
        "exemption is decoration and should be deleted"
    )


def test_the_exemption_covers_the_vendored_copies_and_nothing_else():
    """Two files under `evidence/` are this repository's own, and are audited.

    `PROVENANCE.toml` is the manifest — the file that carried all 55 of the private
    paths this change removes, and 4 of its private links — and `LINKS.md` is the
    note that classifies the vendored records' dead links. Both are authored here, so
    neither is exempt and neither carries a provenance row. Everything else under
    `evidence/` is the other way round.
    """
    for relative in AUTHORED_UNDER_EVIDENCE:
        assert (REPO_ROOT / relative).is_file(), relative
        assert exemption(relative) is None, relative
    for path in AUDITED:
        relative = _relative(path)
        if relative.startswith("evidence/"):
            assert relative in AUTHORED_UNDER_EVIDENCE, relative


# ── coverage pragmas: extracted here, asserted by the coverage work ─────────
def test_a_pragma_is_read_together_with_the_reason_beside_it():
    source = "\n".join(
        (
            "def read(path):",
            "    try:",
            "        return path.read_text()",
            "    except OSError:  # pragma: no cover — needs an unreadable file",
            "        raise",
        )
    )
    found = pragma_reasons(source)
    assert [(entry.line, entry.reason) for entry in found] == [
        (4, "needs an unreadable file")
    ]


def test_a_pragma_with_no_reason_is_reported_with_an_empty_one():
    """The distinction the coverage work needs: present, and unexplained."""
    found = pragma_reasons("    raise  # pragma: no cover\n")
    assert [(entry.line, entry.reason) for entry in found] == [(1, "")]


def test_a_line_without_a_pragma_is_not_reported():
    assert not pragma_reasons("# no cover here, just the words\nx = 1\n")
