"""The claim surface, and the one rule that governs what may be excluded from it.

A coverage percentage is only worth reading if two things are pinned: *what was
measured*, and *what was allowed not to count*. Neither was written down. This
module writes both down and holds them to each other.

**What was measured.** The surface is `plan1`, `box_b`, `arap_core` and the
worked example. It is declared in `pyproject.toml` and read back here rather than
restated, so the number in `README.md`, the configuration the measurement runs
under, and this test cannot drift into describing three different things.

**What was allowed not to count.** Exactly one thing: a `# pragma: no cover` that
carries a reason on the same line. The reason is what makes an exclusion
reviewable — "this line is not covered" is a fact and settles nothing, while
"unreachable while the interval invariant above holds" is an argument someone can
disagree with. A marker with nothing beside it is indistinguishable from a marker
somebody added to make a number go up, and that is the failure this rule exists
to prevent.

**The rule is scoped to the surface, not to the repository.** Test modules and
scripts may write the string `pragma: no cover` freely — `tests/audit.py` and its
tests have to, since the extractor's own tests contain example markers. The rule
applies where the claim applies.
"""

import tomllib

import pytest

from plan1.provenance import REPO_ROOT

from audit import pragma_reasons

#: Where the surface is declared. Read rather than restated — the configuration
#: is what the measurement actually runs under, so anything else here would be a
#: second opinion about it.
PYPROJECT = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
DECLARED_SOURCE = tuple(PYPROJECT["tool"]["coverage"]["run"]["source"])

#: The surface as prose, for the one assertion that has to be independent of the
#: configuration — otherwise a careless edit to `pyproject.toml` would silently
#: shrink what this repository claims, and every test here would still pass.
EXPECTED_SOURCE = ("plan1", "box_b", "arap_core", "examples")


def surface_files():
    """Every Python file on the claim surface, as absolute paths."""
    return sorted(
        path
        for tree in DECLARED_SOURCE
        for path in (REPO_ROOT / tree).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def named(path):
    """A path as the failure message should print it.

    Relative to the repository for the files this actually runs over; unchanged
    for anything else, which in practice means the temporary file the negative
    control below drives the rule with. Building the message must not be able to
    raise — a guard whose *failure* fails is a guard nobody can read."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ── what is measured ────────────────────────────────────────────────────────
def test_the_declared_surface_is_the_one_this_repository_claims():
    """The configuration and the claim, asserted against each other.

    Shrinking the surface is the cheapest possible way to raise a coverage
    percentage, and it leaves no other trace: the number goes up, every test
    still passes, and the prose describing what was measured is somewhere else
    entirely. This is what makes that edit fail."""
    assert DECLARED_SOURCE == EXPECTED_SOURCE


def test_the_measurement_is_branch_aware():
    """A statement-only percentage counts a half-taken `if` as covered. Every
    number this repository publishes about coverage is a branch number, so the
    setting that makes it one is asserted rather than assumed."""
    assert PYPROJECT["tool"]["coverage"]["run"]["branch"] is True


def test_the_threshold_is_the_whole_surface():
    """`fail_under` below 100 would let an unexplained gap open without anyone
    deciding to open it."""
    assert PYPROJECT["tool"]["coverage"]["report"]["fail_under"] == 100


def test_the_surface_is_not_empty_in_a_way_that_would_make_this_vacuous():
    """Every assertion below iterates the surface, so an empty one would pass all
    of them. Four trees, and enough modules to be the thing described."""
    files = surface_files()
    assert len(files) >= 18, [str(p.relative_to(REPO_ROOT)) for p in files]

    trees = {p.relative_to(REPO_ROOT).parts[0] for p in files}
    assert trees == set(EXPECTED_SOURCE)


# ── what may be excluded from it ────────────────────────────────────────────
@pytest.mark.parametrize(
    "path", surface_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_every_coverage_marker_on_the_surface_carries_a_reason(path):
    """One test per file on the surface, so a new file arrives with the rule
    already applied to it rather than needing to be added to a list."""
    unexplained = [
        entry.line for entry in pragma_reasons(path.read_text()) if not entry.reason
    ]
    assert not unexplained, (
        f"{named(path)} has a `# pragma: no cover` with no reason "
        f"beside it at line(s) {unexplained}. Write why the line cannot be "
        f"reached, on the same line as the marker. An exclusion without an "
        f"argument is indistinguishable from one added to make a number go up."
    )


def test_the_rule_has_something_to_be_true_of():
    """The rule gains teeth only from the markers that are actually there, so
    their absence would make every test above pass and mean nothing.

    Two markers, both deliberate: the unreachable interval guard in the
    assembler, and the example's script entry point."""
    marked = {
        str(path.relative_to(REPO_ROOT)): pragma_reasons(path.read_text())
        for path in surface_files()
        if pragma_reasons(path.read_text())
    }
    assert set(marked) == {"plan1/assemble.py", "examples/run_penguin.py"}
    assert all(len(entries) == 1 for entries in marked.values()), marked


@pytest.mark.parametrize(
    "path, fragment",
    [
        ("plan1/assemble.py", "unreachable while the interval invariant"),
        ("examples/run_penguin.py", "pytest imports this module rather than"),
    ],
)
def test_each_marker_says_specifically_why(path, fragment):
    """"Carries a reason" is satisfied by any word at all, so the two reasons in
    the repository are held to saying the particular thing they claim. A reason
    that degrades to "not covered" over some future edit would still pass the
    rule above and would have stopped being an argument."""
    reasons = pragma_reasons((REPO_ROOT / path).read_text())
    assert len(reasons) == 1, reasons
    assert fragment in reasons[0].reason


# ── the rule, driven against something that breaks it ───────────────────────
def test_the_rule_fails_on_a_marker_with_no_reason(tmp_path):
    """The negative control. The assertion above is over files that all pass, so
    on its own it is consistent with a rule that cannot fail — which is a shape
    this repository has shipped twice before and now tests for.

    The real assertion is called rather than reimplemented, so this cannot pass
    while the rule itself is broken."""
    offender = tmp_path / "offender.py"
    offender.write_text("def unreachable():\n    raise SystemExit  # pragma: no cover\n")

    with pytest.raises(AssertionError, match="with no reason"):
        test_every_coverage_marker_on_the_surface_carries_a_reason(offender)


def test_the_rule_passes_a_marker_that_does_carry_a_reason(tmp_path):
    """The other direction, so the control above is showing the rule
    discriminating rather than simply raising.

    Written with an explicit outcome rather than as a bare call that passes by
    not raising. `test_suite_shape.py` rejects the bare form, and it is right to:
    a test whose only check is "reaching the end" is counted, reported green, and
    constrains nothing."""
    compliant = tmp_path / "compliant.py"
    compliant.write_text(
        "def unreachable():\n"
        "    raise SystemExit  # pragma: no cover — needs a signal this process "
        "cannot send itself\n"
    )

    assert [entry.reason for entry in pragma_reasons(compliant.read_text())] == [
        "needs a signal this process cannot send itself"
    ]

    try:
        test_every_coverage_marker_on_the_surface_carries_a_reason(compliant)
    except AssertionError as rejected:
        raise AssertionError(
            f"the rule rejected a marker that does carry a reason: {rejected}"
        ) from rejected
