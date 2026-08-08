"""The mutation record, read back and held to its own claims.

The question a green suite cannot answer is *can these tests fail?* — and this
repository's answer is a measurement rather than an assurance: change one token in
the claim surface, run the whole suite, and see. `scripts/run_mutation.py` performs
the run; `mutation/mutation_record.json` is what it produced; this module is what
stops the record drifting into decoration.

**It does not re-run mutation**, exactly as `test_diagnostic.py` does not regenerate
the solver's committed record. Twenty minutes does not belong in the default suite. What is asserted here is the record's shape and its completeness — above all
that **every survivor carries a justification**, because a survivor with no reason is
a finding that was written down instead of fixed.

The check with the most teeth is the last one: each survivor records the source line
it was found on, and that line is compared against the file as it stands now. Edit a
decision module without re-running the script and the record starts describing a
suite that no longer exists — which is the failure mode a committed measurement has
that a live one does not.
"""

from __future__ import annotations

import json
import re

import pytest

from plan1.provenance import REPO_ROOT, sha256_file
from scripts.run_mutation import CATEGORIES, RECORD, SELF_EXCLUDED, TARGETS

#: The keys a reader needs in order to judge the number rather than take it.
REQUIRED_KEYS = (
    "generated",
    "tool",
    "command",
    "operators",
    "targets",
    "out_of_scope",
    "integrity_checks_excluded",
    "always_excluded",
    "kill_criterion",
    "bytecode",
    "totals",
    "score",
    "survivors",
)


@pytest.fixture(scope="module")
def record():
    assert RECORD.is_file(), (
        f"{RECORD.relative_to(REPO_ROOT)} is missing. The mutation score is a "
        f"committed measurement, not a claim in prose — regenerate it with "
        f"`python scripts/run_mutation.py`."
    )
    return json.loads(RECORD.read_text())


# ── the record is a record ──────────────────────────────────────────────────
def test_the_record_carries_everything_a_reader_needs_to_judge_it(record):
    missing = [key for key in REQUIRED_KEYS if key not in record]
    assert not missing, missing


def test_the_record_is_dated(record):
    """Undated, it describes some version of the suite and a reader cannot say which."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["generated"]), record["generated"]


def test_the_record_names_the_tool_that_produced_it(record):
    tool = record["tool"]
    assert tool["script"] == "scripts/run_mutation.py"
    assert tool["python"] and tool["pytest"]
    assert record["command"].startswith("python scripts/run_mutation.py")


# ── the target set is declared, not implied ─────────────────────────────────
#: The claim surface, stated here **independently of the script that measures it**.
#: Asserting the record against `run_mutation.TARGETS` alone would be circular:
#: narrow the target set, regenerate, and a comparison between the two would still
#: pass while the score quietly came to describe less of the repository. So the set
#: is derived from a property instead — every module under `plan1/` that a published
#: number passes through, plus the edge-weight seam — and the script is held to it.
EXPECTED_TARGETS = (
    "plan1/assemble.py",
    "plan1/manifest.py",
    "plan1/provenance.py",
    "plan1/records.py",
    "plan1/saturation.py",
    "box_b/edge_weights.py",
)


def test_the_record_names_what_was_mutated(record):
    """An unqualified score invites a reader to read a partial measurement as a
    total one, so the target set is named — and named against something other than
    itself."""
    assert sorted(entry["path"] for entry in record["targets"]) == sorted(
        EXPECTED_TARGETS
    )
    assert sorted(TARGETS) == sorted(EXPECTED_TARGETS), (
        "the script's declared target set and the one this suite requires have "
        "diverged; the record would still agree with the script, which is exactly "
        "the circularity this list exists to break"
    )
    for entry in record["targets"]:
        assert (REPO_ROOT / entry["path"]).is_file(), entry["path"]


def test_the_claim_surface_is_every_decision_module_and_not_a_chosen_few():
    """The property behind `EXPECTED_TARGETS`, so the list cannot be quietly pruned.

    `plan1/` is the assembler and everything below it. Exactly one module there is
    presentation — `render.py`, which decides how a number is printed and not what it
    is — and everything else is on the path from an archived record to a published
    cell. Asserted by looking at the directory rather than by reading the list back,
    so a new decision module is caught the moment it lands unmutated.
    """
    present = {
        f"plan1/{path.name}"
        for path in (REPO_ROOT / "plan1").glob("*.py")
        if path.name not in ("__init__.py", "render.py")
    }
    missing = present - set(EXPECTED_TARGETS)
    assert not missing, (
        f"these decision modules are not in the mutation target set, so the score "
        f"says nothing about them: {sorted(missing)}"
    )


def test_the_record_names_what_was_not_mutated_and_why(record):
    """The boundary of the measurement is part of the measurement."""
    assert record["out_of_scope"], "nothing declared out of scope reads as nothing left out"
    for entry in record["out_of_scope"]:
        assert entry["path"]
        assert len(entry["reason"].split()) >= 5, entry


def test_the_record_discloses_the_tests_withheld_from_the_kill_criterion(record):
    """Two sets of tests do not count as kills, and hiding either would inflate the
    score: the ones that fail on a pinned file's bytes changing, and the two that
    are about the harness rather than about the code under mutation."""
    integrity = record["integrity_checks_excluded"]
    assert integrity["applies_to"] == ["box_b/edge_weights.py"]
    assert len(integrity["tests"]) >= 1
    assert "checksum" in integrity["reason"]

    always = record["always_excluded"]
    assert always["tests"] == list(SELF_EXCLUDED)
    assert len(always["reason"].split()) >= 10


# ── the arithmetic is the arithmetic ────────────────────────────────────────
def test_the_totals_add_up(record):
    """Derived here rather than read back, which is the difference between an
    assertion and a restatement."""
    totals = record["totals"]
    per_target = record["targets"]
    for key in ("mutants", "invalid", "killed", "killed_at_collection", "survived"):
        assert totals[key] == sum(entry[key] for entry in per_target), key
    assert totals["applicable"] == totals["mutants"] - totals["invalid"]
    assert totals["killed"] + totals["survived"] == totals["applicable"]
    assert totals["killed_at_collection"] <= totals["killed"]


def test_the_weaker_kind_of_kill_is_counted_separately(record):
    """A mutant that broke on import was never caught by an assertion.

    It is still a kill — the change did not pass unnoticed — but it is evidence
    about the interpreter rather than about the tests, and a score that folded the
    two together would be the more flattering of two readings presented as the only
    one. The record separates them; this asserts the separation is real rather than
    a field that is always zero and therefore never checked.
    """
    kill_criterion = record["kill_criterion"]
    assert "collection" in kill_criterion
    assert "exit 1" in kill_criterion and "exit 2" in kill_criterion
    for entry in record["targets"]:
        assert entry["killed_at_collection"] <= entry["killed"], entry["path"]


def test_the_score_is_the_kill_rate_over_the_mutants_that_compiled(record):
    """A mutant the interpreter rejects was never a test of the tests, so it is
    excluded from the denominator rather than counted as a kill."""
    totals = record["totals"]
    assert record["score"] == pytest.approx(
        totals["killed"] / totals["applicable"], abs=5e-5
    )


def test_the_run_actually_mutated_something(record):
    """The guard on the guard: an empty run scores 0/0 and asserts nothing."""
    assert record["totals"]["applicable"] > 50, record["totals"]


# ── every survivor is argued for ────────────────────────────────────────────
def test_every_survivor_is_listed_rather_than_summarised(record):
    assert len(record["survivors"]) == record["totals"]["survived"]


def test_every_survivor_carries_a_justification(record):
    """The assertion this module exists for.

    A survivor is a place where the suite did not notice the code changing. Listing
    one without saying why that is acceptable turns the record from a measurement
    into a disclosure with the difficult half left out — so the reason is required,
    and it has to be an argument rather than a word.
    """
    unexplained = [
        f"{s['path']}:{s['line']} {s['operator']}"
        for s in record["survivors"]
        if not s.get("reason") or len(s["reason"].split()) < 5
    ]
    assert not unexplained, (
        "these survivors carry no reason, so nothing distinguishes a gap that was "
        "judged acceptable from one nobody looked at:\n  " + "\n  ".join(unexplained)
    )


def test_every_survivor_is_classified_as_one_of_the_three_kinds(record):
    """Equivalent, out of scope, or an accepted gap. Anything else is a finding to
    be fixed rather than an entry to be written."""
    wrong = [
        (s["path"], s["line"], s.get("category"))
        for s in record["survivors"]
        if s.get("category") not in CATEGORIES
    ]
    assert not wrong, wrong


def test_the_record_still_describes_the_code_it_measured(record):
    """The staleness guard, and the one with real reach.

    A committed measurement decays in a way a live one cannot: the code moves on, the
    number does not, and a reader is handed a score for a version of the repository
    nobody can identify. Pinning the *survivor lines* alone is far too weak — there
    are three of them, so every other line of the six targets could change with the
    suite still green.

    So each target's sha256 at measurement time is recorded, and compared here
    against the file as it stands. Editing anything on the claim surface therefore
    fails this test, and the fix is to re-run the measurement rather than to edit the
    number. That is deliberately strict: the alternative is a record that describes a
    suite that no longer exists and says so nowhere.
    """
    stale = []
    for entry in record["targets"]:
        path = REPO_ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        if sha256_file(path) != entry["sha256"]:
            stale.append(entry["path"])
    assert not stale, (
        "these targets have changed since the mutation record was written, so the "
        "score describes code that is no longer here. Re-run "
        "`python scripts/run_mutation.py`:\n  " + "\n  ".join(stale)
    )


def test_every_survivor_still_sits_on_the_line_the_record_recorded(record):
    """The record has to describe the suite that exists, not one that used to.

    A committed measurement decays silently: the code moves, the record does not,
    and a reader is handed a score for a version of the repository nobody can
    identify. Comparing the recorded source line against the file as it stands makes
    that decay a failure — regenerate the record, or explain why the line moved.
    """
    stale = []
    for survivor in record["survivors"]:
        lines = (REPO_ROOT / survivor["path"]).read_text().splitlines()
        if not 1 <= survivor["line"] <= len(lines):
            stale.append(f"{survivor['path']}:{survivor['line']} is past end of file")
        elif lines[survivor["line"] - 1].strip() != survivor["source"]:
            stale.append(
                f"{survivor['path']}:{survivor['line']} records "
                f"{survivor['source']!r}, file now has "
                f"{lines[survivor['line'] - 1].strip()!r}"
            )
    assert not stale, (
        "the record describes source that has moved since it was written:\n  "
        + "\n  ".join(stale)
    )


# ── and it stays out of the gate ────────────────────────────────────────────
def test_the_mutation_run_is_not_wired_into_the_one_command_gate():
    """Twenty minutes in `verify.sh` is a gate nobody waits for, and a gate
    nobody runs is worth less than the record it would have produced."""
    assert "run_mutation" not in (REPO_ROOT / "scripts" / "verify.sh").read_text()
