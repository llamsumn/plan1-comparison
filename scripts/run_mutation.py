#!/usr/bin/env python3
"""Measure whether this repository's tests can fail, and record the answer.

    python scripts/run_mutation.py            # the full run, about 20 minutes
    python scripts/run_mutation.py --list     # what it would mutate, without running

A green suite says the tests ran. It does not say they constrain anything, and the
difference is not academic here: before this script existed, the comparison that
selects the published row could be changed from inclusive to exclusive and all 627
tests still passed. Coverage did not predict it and ran against it — the module with
the surviving mutants reported 100% line coverage, and the module whose every mutant
died reported 86%. A line can be executed and still constrain nothing.

So: change one token in the source, run the whole suite, and see whether anything
notices. A mutant the suite catches is **killed**; one it does not is a **survivor**,
and every survivor is written into the record with the reason it is acceptable. A
survivor with no reason is a finding, not an entry.

**What is mutated.** Tokens, not text. The source is tokenised and only operator and
name tokens are touched, so comments and docstrings are structurally out of reach —
a naive textual mutator produces large numbers of "survivors" inside prose, and a
record padded with those measures nothing. Mutants that do not compile are counted
separately and excluded from the score rather than counted as kills, because a
mutant the interpreter rejects was never a test of the tests.

**How a kill is counted, and the weaker kind.** pytest answers in exit codes, and
the two failing ones are not the same evidence. Exit 1 is a test that ran and failed
— an assertion caught the change. Exit 2 is a collection error: the mutant compiled
but broke on import, so the suite never got as far as asserting anything. Both are
kills, because in neither case did the change pass unnoticed, but only the first is
evidence about the *tests*. They are counted separately and reported separately, so
a score can be read down to the assertions that earned it.

**What is not mutated** is declared rather than implied: `TARGETS` below is the claim
surface, `OUT_OF_SCOPE` names what was left out and why. An unqualified score over an
undeclared target set invites a reader to read a partial measurement as a total one.

**The one exclusion from the kill criterion.** `box_b/edge_weights.py` is pinned by
sha256 in `evidence/PROVENANCE.toml` and its hash is printed in the published table's
footer, so *any* byte changing there fails eight tests before behaviour enters into
it. Counting those as kills would report the strongest module in the repository on
the strength of a checksum. They are excluded for that one file, named in
`INTEGRITY_CHECKS`, and the record says so.

This is deliberately **not** part of `scripts/verify.sh`. It takes about twenty
minutes, and a green gate nobody waits for is not a gate. The artefact is the record.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: Where the record lives. Beside the solver's committed diagnostic, which is the
#: same shape of artefact: written by a script, read back and asserted by a test that
#: never regenerates it.
RECORD = REPO / "mutation" / "mutation_record.json"

#: The claim surface. Every module a published number passes through on its way from
#: an archived record to a cell in the table.
TARGETS: tuple[str, ...] = (
    "plan1/assemble.py",
    "plan1/saturation.py",
    "plan1/records.py",
    "plan1/manifest.py",
    "plan1/provenance.py",
    "box_b/edge_weights.py",
)

#: What was left out, and why. Named here so the score is read as what it is.
OUT_OF_SCOPE: tuple[tuple[str, str], ...] = (
    (
        "plan1/render.py",
        "presentation. It decides how a number is printed, not what it is; a "
        "surviving mutant there is a formatting question and the committed table "
        "is diffed byte-for-byte anyway.",
    ),
    (
        "scripts/",
        "entry points. They read a manifest, call the seam and print; the "
        "decisions are all below them.",
    ),
    (
        "diagnostics/",
        "the solver's own evidence, already re-executed rather than re-read by "
        "tests/test_diagnostic.py — a stronger check than mutation gives.",
    ),
    (
        "arap_core/",
        "the ported solver. Its ladder is driven end to end by the diagnostic and "
        "compared field by field against a committed record; widening the target "
        "set to it is a future decision rather than an oversight.",
    ),
    (
        "tests/",
        "mutating a test measures nothing about the tests.",
    ),
)

#: Operator substitutions. Deliberately small: each one changes a decision rather
#: than a value, and each is syntactically valid wherever the token it replaces is.
OPERATORS: dict[str, str] = {
    "<": "<=",
    "<=": "<",
    ">": ">=",
    ">=": ">",
    "==": "!=",
    "!=": "==",
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*",
}

#: Keyword substitutions. `is` is only ever a comparison, so `is not` is always
#: valid; `in` is not — `for x not in y` does not compile — and those are counted as
#: invalid rather than dropped, so the record's arithmetic stays checkable.
KEYWORDS: dict[str, str] = {
    "and": "or",
    "or": "and",
    "True": "False",
    "False": "True",
    "is": "is not",
    "in": "not in",
}

#: The eight tests that fail on `box_b/edge_weights.py` changing by a single byte,
#: measured rather than guessed: its sha256 is recorded in `evidence/PROVENANCE.toml`
#: and printed in the published footer, and `scripts/build_table.py` refuses to
#: render when the two disagree. They are excluded from the kill criterion for that
#: file alone — for every other target they are ordinary behavioural tests and stay
#: in.
INTEGRITY_CHECKS: tuple[str, ...] = (
    "tests/test_build_table.py::test_the_committed_table_regenerates_byte_identically",
    "tests/test_build_table.py::test_the_rendered_table_names_no_absolute_path",
    "tests/test_build_table.py::test_the_rendered_table_resolves_nothing_outside_the_repository",
    "tests/test_build_table.py::test_the_assembly_date_is_declared_rather_than_stamped_at_run_time",
    "tests/test_build_table.py::test_the_footer_names_every_recorded_artefact",
    "tests/test_conformance.py::test_the_vendored_reference_rule_is_the_one_that_was_ported",
    "tests/test_ported_method.py::test_every_ported_file_hashes_to_its_recorded_value",
    "tests/test_ported_method.py::test_the_published_table_still_names_nothing_outside_the_repository",
)

#: The targets whose bytes are pinned, and so the only ones `INTEGRITY_CHECKS` is
#: withheld for.
HASH_PINNED: frozenset[str] = frozenset({"box_b/edge_weights.py"})

#: Withheld for every target, and neither of them is a judgement call.
#:
#: `test_mutation_record.py` reads the file this script is writing, so during a run
#: its verdict is about the previous record rather than about the mutant.
#:
#: `test_the_collected_total_matches_the_expected_total` counts the session's items,
#: and pytest removes a deselected test from that count — so *any* deselection makes
#: it fail, on every mutant, for a reason that has nothing to do with the mutant. It
#: can only be a genuine killer if a mutation changes how many tests exist, which a
#: change inside a decision module cannot do without raising at collection, and a
#: collection error fails the run anyway.
SELF_EXCLUDED: tuple[str, ...] = (
    "tests/test_mutation_record.py",
    "tests/test_suite_shape.py::test_the_collected_total_matches_the_expected_total",
)

#: How a survivor may be accounted for. Anything outside these three is a finding to
#: be fixed rather than an entry to be written.
CATEGORIES: tuple[str, ...] = (
    "equivalent",  # the mutant computes the same thing as the original
    "out_of_scope",  # the mutated line is not part of the claim surface
    "accepted_gap",  # a real gap, judged not worth a test, with the reason stated
)


@dataclass(frozen=True)
class Mutant:
    """One token, and what it was changed to."""

    path: str
    line: int
    column: int
    end_column: int
    original: str
    replacement: str

    @property
    def operator(self) -> str:
        return f"{self.original} -> {self.replacement}"

    def key(self) -> tuple[str, int, str]:
        return (self.path, self.line, self.operator)


def mutants(relative: str) -> list[Mutant]:
    """Every single-token mutation available in one file.

    Tokenised rather than searched. That is the whole reason comments and docstrings
    cannot contribute: they arrive as `COMMENT` and `STRING` tokens and are never
    looked at, so no amount of prose about `<=` produces a mutant.
    """
    source = (REPO / relative).read_text()
    found: list[Mutant] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        replacement: str | None = None
        if token.type == tokenize.OP:
            replacement = OPERATORS.get(token.string)
        elif token.type == tokenize.NAME:
            replacement = KEYWORDS.get(token.string)
        elif token.type == tokenize.NUMBER and token.string.isdigit():
            # An integer literal is a threshold as often as an operator is: the
            # console reader's search window is a `3`, and the sweep-length rule a
            # `2`. Stepping it by one is the off-by-one those two would suffer.
            replacement = str(int(token.string) + 1)
        if replacement is None:
            continue
        (line, column), (end_line, end_column) = token.start, token.end
        if line != end_line:  # no operator or keyword spans a line
            continue
        found.append(
            Mutant(
                path=relative,
                line=line,
                column=column,
                end_column=end_column,
                original=token.string,
                replacement=replacement,
            )
        )
    return found


def apply(source: str, mutant: Mutant) -> str:
    """`source` with the one token replaced."""
    lines = source.splitlines(keepends=True)
    line = lines[mutant.line - 1]
    lines[mutant.line - 1] = (
        line[: mutant.column] + mutant.replacement + line[mutant.end_column :]
    )
    return "".join(lines)


def source_line(source: str, mutant: Mutant) -> str:
    return source.splitlines()[mutant.line - 1].strip()


def sha256_file(path: Path) -> str:
    """What the target hashed to when it was measured.

    This is what stops the record quietly describing a version of the code that no
    longer exists. A committed measurement decays in a way a live one cannot: the
    source moves on, the number does not, and a reader is handed a score for a
    repository nobody can identify. Recording the digest makes that decay a test
    failure — `tests/test_mutation_record.py` compares each one against the file as
    it stands, so editing anything in the claim surface says, in the suite, that the
    record is now stale.

    Deliberately not imported from `plan1.provenance`, which has the same function:
    this script must be runnable and readable on its own, and a mutation of the
    provenance module during a run must not be able to reach the measurement that is
    recording it.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def compiles(source: str, relative: str) -> bool:
    try:
        compile(source, relative, "exec")
    except SyntaxError:
        return False
    return True


def purge_bytecode(relative: str) -> None:
    """Delete any cached bytecode for a target, before it is mutated.

    **Not housekeeping — a correctness fix, and it was found the hard way.** CPython
    decides a `.pyc` is current by comparing the source's modification time *in whole
    seconds* and its size. Mutation changes one token, so the size very often does
    not move (`+` for `-`, `0` for `1`, `==` for `!=`), and a write followed by a
    restore inside the same second therefore produces a file whose bytecode cache
    still holds the *mutant*. The suite then runs against code that is not on disk,
    and the verdict is about neither version.

    That is not hypothetical: two tests written in this session passed when run
    alone and failed minutes later against untouched sources, because a restored file
    was still executing its mutant's bytecode. Combined with `-B` below — which stops
    any new cache being written during the run — this removes the failure mode rather
    than making it unlikely.
    """
    module = REPO / relative
    cache = module.parent / "__pycache__"
    if cache.is_dir():
        for stale in cache.glob(f"{module.stem}.*.pyc"):
            stale.unlink()


def run_suite(deselect: tuple[str, ...]) -> int:
    """Run the whole suite once and return pytest's exit code.

    0 means nothing noticed and the mutant survived; 1 means a test ran and failed;
    2 or more means the suite could not be collected, which is a kill of the weaker
    kind — see the module docstring. The code is returned rather than a boolean
    precisely so the two kinds stay distinguishable in the record.

    `-x` because one failing test is the whole answer: a mutant is killed the moment
    anything catches it, and the remaining tests would only tell us how loudly.

    `-B` so the run writes no bytecode cache at all; see `purge_bytecode`.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-x",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *[f"--deselect={node}" for node in deselect],
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return result.returncode


def carried_reasons(record_path: Path) -> dict[tuple[str, int, str], dict[str, str]]:
    """The justifications already written, so regenerating does not erase them.

    The script produces the measurement; the reason a survivor is acceptable is an
    argument a person makes. Keying on file, line and operator means a survivor whose
    line has moved comes back unexplained — which is correct, because the argument
    was about that line.
    """
    if not record_path.is_file():
        return {}
    carried = {}
    for entry in json.loads(record_path.read_text()).get("survivors", []):
        carried[(entry["path"], entry["line"], entry["operator"])] = {
            "category": entry.get("category", ""),
            "reason": entry.get("reason", ""),
        }
    return carried


def tool_versions() -> dict[str, str]:
    import pytest

    return {
        "script": "scripts/run_mutation.py",
        "python": ".".join(str(n) for n in sys.version_info[:3]),
        "pytest": pytest.__version__,
    }


def run(targets: tuple[str, ...], record_path: Path) -> dict:
    carried = carried_reasons(record_path)
    per_target: list[dict] = []
    survivors: list[dict] = []
    totals = {
        "mutants": 0,
        "invalid": 0,
        "killed": 0,
        "killed_at_collection": 0,
        "survived": 0,
    }

    for relative in targets:
        path = REPO / relative
        purge_bytecode(relative)
        original = path.read_text()
        deselect = SELF_EXCLUDED + (
            INTEGRITY_CHECKS if relative in HASH_PINNED else ()
        )
        counts = {
            "mutants": 0,
            "invalid": 0,
            "killed": 0,
            "killed_at_collection": 0,
            "survived": 0,
        }
        try:
            for mutant in mutants(relative):
                counts["mutants"] += 1
                mutated = apply(original, mutant)
                if not compiles(mutated, relative):
                    counts["invalid"] += 1
                    continue
                path.write_text(mutated)
                exit_code = run_suite(deselect)
                path.write_text(original)
                survived = exit_code == 0
                counts["survived" if survived else "killed"] += 1
                if exit_code >= 2:
                    counts["killed_at_collection"] += 1
                verdict = (
                    "SURVIVED"
                    if survived
                    else ("killed" if exit_code == 1 else "killed at collection")
                )
                print(
                    f"  {relative}:{mutant.line} {mutant.operator:<16} {verdict}",
                    file=sys.stderr,
                    flush=True,
                )
                if survived:
                    written = carried.get(mutant.key(), {"category": "", "reason": ""})
                    survivors.append(
                        {
                            "path": mutant.path,
                            "line": mutant.line,
                            "operator": mutant.operator,
                            "source": source_line(original, mutant),
                            "category": written["category"],
                            "reason": written["reason"],
                        }
                    )
        finally:
            # Restore whatever happened. A crash mid-run must not leave a mutated
            # decision module in the working tree.
            path.write_text(original)

        per_target.append(
            {"path": relative, "sha256": sha256_file(path), **counts}
        )
        for key, value in counts.items():
            totals[key] += value

    applicable = totals["mutants"] - totals["invalid"]
    return {
        "generated": date.today().isoformat(),
        "tool": tool_versions(),
        "command": "python scripts/run_mutation.py",
        "operators": {**OPERATORS, **KEYWORDS, "<integer literal>": "n + 1"},
        "targets": per_target,
        "out_of_scope": [{"path": p, "reason": r} for p, r in OUT_OF_SCOPE],
        "integrity_checks_excluded": {
            "applies_to": sorted(HASH_PINNED),
            "tests": list(INTEGRITY_CHECKS),
            "reason": (
                "These fail on the file's bytes changing rather than on its "
                "behaviour changing: its sha256 is recorded in "
                "evidence/PROVENANCE.toml and printed in the published table's "
                "footer, and the table refuses to render when the two disagree. "
                "Counting them as kills would report a checksum as test strength."
            ),
        },
        "bytecode": (
            "Cached bytecode is purged for each target before it is mutated and no "
            "new cache is written during the run (`python -B`). CPython treats a "
            "`.pyc` as current when the source's whole-second mtime and size both "
            "match, and a one-token mutation usually leaves the size unchanged — so "
            "without this the suite can run against a mutant that is no longer on "
            "disk."
        ),
        "always_excluded": {
            "tests": list(SELF_EXCLUDED),
            "reason": (
                "The first is the record's own reader module. Twelve of its "
                "fourteen tests read the file this run writes, so during a run "
                "their verdict is about the previous record rather than about the "
                "mutant; it is deselected whole rather than by node so the list "
                "cannot drift as tests are added to it, which withholds the two "
                "that do not read the record as well. The second counts the "
                "session's collected tests, and pytest removes a deselected test "
                "from that count, so any deselection fails it on every mutant for "
                "a reason unrelated to the mutant."
            ),
        },
        "kill_criterion": (
            "A mutant is killed when the suite does not come back green. pytest "
            "exit 1 is a test that ran and failed — an assertion caught the change "
            "— and exit 2 is a collection error, where the mutant compiled but "
            "broke on import so nothing was ever asserted. Both are kills, because "
            "in neither case did the change pass unnoticed, but only the first is "
            "evidence about the tests. `killed_at_collection` counts the second "
            "kind separately, per target and in the totals, so the score can be "
            "read down to the assertions that earned it."
        ),
        "totals": {**totals, "applicable": applicable},
        "score": round(totals["killed"] / applicable, 4) if applicable else None,
        "survivors": survivors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="count the available mutants and exit, without running the suite",
    )
    parser.add_argument(
        "--target",
        action="append",
        metavar="PATH",
        help="mutate only this target (repeatable); defaults to the whole claim surface",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=RECORD,
        help=(
            "write the record here instead of over the committed one; used to try "
            "a run without clobbering the measurement in the repository"
        ),
    )
    args = parser.parse_args(argv)

    targets = tuple(args.target) if args.target else TARGETS
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        print(f"not in the declared target set: {unknown}", file=sys.stderr)
        return 1

    if args.list:
        total = 0
        for relative in targets:
            available = mutants(relative)
            total += len(available)
            print(f"{relative}: {len(available)}")
        print(f"total: {total}")
        return 0

    record = run(targets, args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n")

    unexplained = [s for s in record["survivors"] if not s["reason"]]
    print(
        f"\n{record['totals']['killed']}/{record['totals']['applicable']} killed "
        f"({record['totals']['killed_at_collection']} of them at collection rather "
        f"than by an assertion), score {record['score']}, "
        f"{record['totals']['survived']} survived, "
        f"{record['totals']['invalid']} did not compile. Wrote {args.out}.",
        file=sys.stderr,
    )
    if unexplained:
        print(
            f"{len(unexplained)} survivor(s) carry no reason. A survivor with no "
            f"reason is a finding, not an entry — write the argument or fix the "
            f"gap before committing the record.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
