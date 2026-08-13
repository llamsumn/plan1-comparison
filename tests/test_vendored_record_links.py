"""Every link in the vendored records leads somewhere, or is accounted for.

`README.md` states the principle: *a citation that resolves nowhere is worse than
none — it claims the rules were fixed in advance while making the claim uncheckable.*
The repository applied it once, by vendoring the pre-registration and the verdict
that govern the published table. It then stopped one level short, because those two
documents carry the same defect *inside* them: eleven relative links, written where
the documents were written, pointing at paths that are not here.

They cannot be fixed the obvious way. Every byte under `evidence/` is pinned by
sha256, and that pin is the only thing that lets a reader holding an original audit
this copy against it. Rewriting a link would change the bytes and spend exactly that.

So the links are **worked around, never written over**. Two of the eleven resolved by
*placement*: the Phase-B probe verdict and the feasibility addendum, the two
companions these records cite by name, are now vendored beside them, so those
citations resolve with nothing edited. Both of those documents arrived with dead links
of their own, which is why the tally runs over five documents rather than two:

| of 44 links in the five documents | targets | instances |
|---|---|---|
| resolve as written | 3 | 12 |
| redirects — the same content under `evidence/` | 8 | 12 |
| exclusions — documents that deliberately did not travel | 11 | 20 |

`evidence/record/LINKS.md` is where a reader meets that classification. This module
is what keeps it complete: a link nobody classified fails here rather than reaching
an examiner as a 404, and so does a document dropped into this directory with links
of its own — which is the failure that vendoring two more records could otherwise
have introduced.

**The fifth document is what this module was written for.** Publishing the second
asset vendored `trex_comparison_prereg.md`, which arrived carrying fifteen links, ten
of them to targets that are not here. Every one failed this module until it was
classified — including two that are genuine *records* rather than plans, and which
`LINKS.md` argues out on the ground that what they establish is present as enforced
evidence rather than as a copied claim.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from audit import (
    AUTHORED_UNDER_EVIDENCE,
    LINK_KINDS,
    RelativeLink,
    link_classifications,
    relative_links,
)
from plan1.provenance import EVIDENCE_ROOT, REPO_ROOT

RECORD_DIR = EVIDENCE_ROOT / "record"
NOTE = RECORD_DIR / "LINKS.md"


def vendored_records() -> list[Path]:
    """The copied documents in `evidence/record/` — the note itself is not one."""
    authored = {REPO_ROOT / relative for relative in AUTHORED_UNDER_EVIDENCE}
    return sorted(
        path for path in RECORD_DIR.glob("*.md") if path not in authored
    )


CLASSIFIED = link_classifications(NOTE.read_text())

#: Every link, as (document, link) pairs, so a failure names both.
LINKS = [(document, link)
         for document in vendored_records()
         for link in relative_links(document.read_text())]


def _identify(case: tuple[Path, RelativeLink]) -> str:
    document, link = case
    return f"{document.name}:{link.line} -> {link.target}"


@pytest.mark.parametrize("case", LINKS, ids=_identify)
def test_every_link_in_a_vendored_record_resolves_or_is_accounted_for(case):
    """The enumeration, per link, so the failure names the link and not the file.

    Both branches assert. A link that resolves must *not* also carry a note entry:
    two accounts of one link is how a note starts describing a repository that has
    moved on, and it is the shape `test_the_note_classifies_nothing_that_is_not_linked`
    catches in the aggregate. Returning early on the 8 that resolve would leave 8 of
    these 29 cases passing without asserting anything, in a suite whose own total is
    asserted.
    """
    document, link = case
    classified = CLASSIFIED.get(link.target)
    if link.resolves_from(document):
        assert classified is None, (
            f"{document.name}:{link.line} links to `{link.target}`, which resolves "
            f"as written — so {NOTE.name} should not also classify it as "
            f"{classified!r}. One link, one account."
        )
        return
    assert classified in LINK_KINDS, (
        f"{document.name}:{link.line} links to `{link.target}`, which is not in "
        f"this repository and is not classified in "
        f"{NOTE.relative_to(REPO_ROOT)}. Nothing under evidence/ may be edited, so "
        f"the fix is a redirect or an exclusion entry in that note — never a "
        f"rewritten link."
    )


@pytest.mark.parametrize("document", vendored_records(), ids=lambda p: p.name)
def test_every_vendored_record_is_covered_by_the_note(document):
    """A record dropped in here without being read is the failure this catches.

    Vendoring two more documents was how this change made two dead citations
    resolve, and each of those documents arrived with dead links of its own. Had
    nobody looked, the fix would have re-imported the defect it was closing. So the
    note names every document in this directory, and a new one fails until it does.
    """
    assert f"`{document.name}`" in NOTE.read_text(), (
        f"{document.name} is vendored here but {NOTE.name} does not name it. Read "
        f"its links and classify them before it ships."
    )


#: The document the two negative controls hang a fabricated link off. Any of the four
#: would do; this is the one whose directory the fabricated targets are resolved
#: against.
A_RECORD = RECORD_DIR / "plan1_prereg.md"


def test_the_link_guard_fails_on_a_dead_link_nobody_classified():
    """The guard above, driven against a deliberately bad link.

    This is the failure the note exists to prevent, so it is watched rather than
    assumed — the practice `tests/test_conformance.py`'s negative controls establish,
    and the same one the two manifest row guards carry.

    The real guard is called, not reimplemented. A control asserting against its own
    copy of the predicate would keep passing while the guard was edited into
    uselessness.
    """
    dead = RelativeLink(
        line=1,
        label="a citation",
        target="../../docs/specs/a-document-nobody-classified.md",
    )
    assert not dead.resolves_from(A_RECORD), "fixture assumption"
    assert dead.target not in CLASSIFIED

    with pytest.raises(AssertionError, match="not classified"):
        test_every_link_in_a_vendored_record_resolves_or_is_accounted_for(
            (A_RECORD, dead)
        )


def test_the_link_guard_fails_on_a_note_entry_for_a_link_that_works(monkeypatch):
    """The other direction, which is the one that rots.

    An entry explaining where a target went, kept after the target stopped going
    anywhere, is a note describing a repository that has moved on. `CLASSIFIED` is
    patched rather than the note edited, because the note is the artefact under test.
    """
    working = RelativeLink(line=1, label="a citation", target="plan1_prereg.md")
    assert working.resolves_from(A_RECORD), "fixture assumption"
    monkeypatch.setitem(CLASSIFIED, working.target, "redirect")

    with pytest.raises(AssertionError, match="One link, one account"):
        test_every_link_in_a_vendored_record_resolves_or_is_accounted_for(
            (A_RECORD, working)
        )


def test_the_note_classifies_nothing_that_is_not_linked():
    """A stale entry is a claim about a link that no longer exists.

    The note is prose and prose rots. If a record stopped citing something, the
    entry explaining where it went should go too — otherwise the note accumulates
    answers to questions nobody asks, and a reader cannot tell which entries are
    live.
    """
    linked = {link.target for _, link in LINKS}
    stale = sorted(target for target in CLASSIFIED if target not in linked)
    assert not stale, (
        f"{NOTE.name} classifies links that no document here carries: {stale}"
    )


def test_the_note_is_not_vacuous():
    """Both checks above pass against a note that classifies nothing.

    29 links over the four documents: 8 instances of 3 targets that resolve as
    written, 9 of 5 redirects, 12 of 6 exclusions. Both halves are asserted —
    targets, because that is what the note's tables enumerate, and *instances*,
    because the note states them in its own prose and a count stated in prose is
    exactly what goes quietly wrong.
    """
    kinds = sorted(CLASSIFIED.values())
    assert kinds.count("redirect") == 8, kinds
    assert kinds.count("exclusion") == 11, kinds
    assert len(vendored_records()) == 5, [p.name for p in vendored_records()]

    instances = {"resolving": 0, "redirect": 0, "exclusion": 0}
    for document, link in LINKS:
        if link.resolves_from(document):
            instances["resolving"] += 1
        else:
            instances[CLASSIFIED[link.target]] += 1
    assert instances == {"resolving": 12, "redirect": 12, "exclusion": 20}, instances
    assert len(LINKS) == 44, len(LINKS)

    # The note states all six of those numbers in words. They are read back out here,
    # so the prose cannot drift from the links the way it did on first writing — the
    # resolving and exclusion instance counts were each a digit out, and the two
    # errors happened to cancel in the total. Whitespace is normalised first: the
    # numbers are the claim, and where a sentence happens to wrap is not.
    prose = " ".join(NOTE.read_text().split())
    for stated in (
        "3 targets, over 12 link instances",
        "8 targets, over 12 instances",
        "11 targets, over 20 instances",
    ):
        assert stated in prose, stated


def test_the_front_page_states_the_link_counts_these_documents_actually_have():
    """`README.md` describes this classification, and its numbers went stale too.

    It read *"Twenty-one links across the four documents … at eleven distinct
    targets … five targets as redirects, six as documents that deliberately did not
    travel … any of the 29 links in the four"* while there were five documents and
    44 links. Same defect as the suite total on the same page: published where a
    reader lands, cross-referenced to the module that enforces it, and compared to
    it by nothing.

    Recomputed here from the documents rather than restated, so the paragraph is a
    claim about this repository instead of about the one it was written for. The
    note beside the records already works this way — `test_the_note_is_not_vacuous`
    reads its six numbers back — and the front page had no equivalent.
    """
    text = " ".join((REPO_ROOT / "README.md").read_text().split())

    outward = [(d, link) for d, link in LINKS if not link.resolves_from(d)]
    expected = {
        "outward": len(outward),
        "documents": len(vendored_records()),
        "targets": len({link.target for _, link in outward}),
        "redirects": sum(1 for kind in CLASSIFIED.values() if kind == "redirect"),
        "exclusions": sum(1 for kind in CLASSIFIED.values() if kind == "exclusion"),
        "total": len(LINKS),
    }

    stated = re.search(
        r"\*\*(?P<outward>\d+)\*\* links across the \*\*(?P<documents>\d+)\*\* documents "
        r"still point outward, at \*\*(?P<targets>\d+)\*\* distinct targets",
        text,
    )
    assert stated, "README.md no longer states how many links point outward"

    classified = re.search(
        r"\*\*(?P<redirects>\d+)\*\* targets as redirects, \*\*(?P<exclusions>\d+)\*\* "
        r"as documents that deliberately did not travel",
        text,
    )
    assert classified, "README.md no longer states how the outward links are classified"

    total = re.search(r"any of the \*\*(?P<total>\d+)\*\* links in the five", text)
    assert total, "README.md no longer states the total the guard walks"

    published = {
        key: int(value)
        for match in (stated, classified, total)
        for key, value in match.groupdict().items()
    }
    assert published == expected, f"README.md publishes {published}; the documents have {expected}"


def test_the_two_companions_resolve_by_placement_rather_than_by_edit():
    """The claim the vendoring rests on, asserted rather than described.

    The pre-registration cites the Phase-B probe verdict; the verdict cites the
    feasibility addendum. Both were sibling-relative links into a directory a reader
    does not have. Both now resolve — and neither citing document was touched, which
    is what the unchanged sha256 on its row in `PROVENANCE.toml` proves.
    """
    for citing, cited in (
        ("plan1_prereg.md", "phase_b_probe_verdict.md"),
        ("plan1_verdict.md", "plan1_feasibility_addendum.md"),
    ):
        document = RECORD_DIR / citing
        targets = [link.target for link in relative_links(document.read_text())]
        assert cited in targets, f"{citing} no longer cites {cited}"
        assert (RECORD_DIR / cited).is_file(), cited
        assert cited not in CLASSIFIED, (
            f"{cited} resolves by placement; classifying it as well would mean the "
            f"note and the directory disagree"
        )
