# CONTEXT — plan1-comparison

_The single-context orientation doc for this repository. Read this before changing anything._

## What this repository is

One published comparison table, and the whole evidence chain behind it, kept as a single
reviewable unit that a reader can clone and check.

The test every decision here is measured against:

> *Does a bare clone, on a machine that has never seen anything else, reproduce what is
> claimed?*

That is not an aspiration about code quality — it is a load-bearing constraint, and most of
what looks unusual here follows from it. Everything in this repository must be true,
checkable, and resolvable without leaving it.

## The vendoring discipline

Everything this repository reads at run time is under `evidence/`, and every byte of it is
recorded in `evidence/PROVENANCE.toml` — what it is, its sha256, and why it travelled.
Derived artefacts additionally record the command that produced them, the date, and the
verdict that certifies them.

**`origin` says what a file is, not where a copy of it once sat.** Each row used to record
an absolute path on the authoring machine, and that was worth less than it looked: a reader
cannot resolve it, and for 24 of the rows it was character-identical to the file's own
location here once the private prefix came off. `origin` records the measurement instead —
which run, which evaluation step, which study step, which document — and the guard on it is
that it names no path, no repository and no ticket. What makes the copy auditable is the
hash, and that has not changed.

The record is asserted **in both directions**, by `tests/test_vendored_evidence.py`:

- a recorded file that no longer hashes to its recorded value **fails**, and
- a file that arrived under `evidence/` with no row **fails just as loudly**.

The second direction is the one that is easy to omit and does most of the work. A
one-directional check lets evidence accumulate quietly, unrecorded and unexplained, and a
reader has no way to tell an oversight from a decision.

### Why a copy and not a live binding — the trade, stated

**Vendoring gives up divergence detection.** A copy cannot notice that its original changed.
This was traded away deliberately, for self-containment, and the reason is specific to this
work rather than general:

> Divergence detection protects a **living** codebase — it tells you that something you still
> depend on has moved underneath you. **This evidence is frozen.** It is nine archived runs
> that will never be re-run, a deployed cluster source fixed at a cited hash, and a reference
> rule as it stood at the commit that produced the evidence. "Notice if upstream moves"
> protects nothing about that claim, because nothing upstream moving could make the claim
> more or less true. Self-containment, by contrast, is exactly what a reader needs.

Without that paragraph a reader reads the vendored copy as an oversight. It is not; it is the
decision, and `PROVENANCE.toml` is what keeps it honest — anyone holding an original can
audit every copied byte against it.

**The cost is real and is stated rather than hidden.** If an original run record were edited
tomorrow, nothing here would report it. What is defended instead is that the copy is
identifiable: a reader can always tell *which* bytes this table was built from.

## What is deliberately excluded

| not here | why |
|---|---|
| `box_b/descriptors.py`, `box_b/noise.py` and their 47 tests | the geometry reader. Paused on a diagnosed shrinking-ball defect, so nothing here rests on it. The B2 seam (`box_b/edge_weights.py`) is complete and standing, and it is the only part that travels. |
| the characterisation study's **code** | results travel, code is cited. Its outputs are under `evidence/characterisation/` with the command that wrote each one; forking a living study into a frozen artifact would hand a reader two versions to reconcile. |
| a second asset's (trex) sweep, ~1.4 MB | no manifest row binds it, no published number derives from it. Recorded as an exclusion with a reason, not silently absent. |
| the assembly spec that governs this work, and its parent — 869 lines between them | planning documents, superseded by their own outputs. What they decided that still binds — the comparability gate, the precision policy and the saturation rule — is stated below and asserted in the suite; the pre-registration and verdict they produced are vendored verbatim at `evidence/record/`. |
| four further planning documents the vendored records link to | records travel, plans do not. Three of them cite code by absolute path under a home directory, which is the defect this repository removed; one says of itself that it is not canonical. Each is named in `evidence/record/LINKS.md` with what it was and why it stayed behind. |

Exclusions are written down. "The evidence base" has to be a **closed** statement — a reader
must be able to tell the difference between something that was considered and left out, and
something nobody thought of.

## The three things this repository enforces

Stated fully in `README.md`; named here so the orientation is complete.

1. **Rows must demonstrably have begun from the same state** — the comparability gate keys on
   the step-0 metric triple, the primitive count and the evaluation step. Failure raises; it
   never warns.
2. **No number is printed at a precision its source does not have** — and a published cell
   printed at coarser precision denotes an interval too, so comparison against one is made
   interval to interval. A "correction" that came from ignoring this was retracted, and the
   guard that replaced it compares interval to interval.
3. **The reported row is selected by a rule declared in advance** — smallest rigidity whose
   PSNR falls within the replicate band of the sweep maximum, or no row is published at all.
   The rule is vendored at `evidence/record/plan1_prereg.md`.

## Conventions

- **`out/comparison_table.md` is generated, never hand-edited.** It regenerates
  byte-identically and `tests/test_build_table.py` asserts exactly that. Adding a run is a
  manifest edit; no number is ever retyped.
- **Nothing under `evidence/` is edited.** Copying is not editing; anything else breaks the
  hash that makes the copy auditable. Two files there are exceptions, and both for the same
  reason — this repository *wrote* them, so there is no original to audit them against:
  `PROVENANCE.toml`, the manifest, and `record/LINKS.md`, the note that classifies the
  vendored records' dead links. `tests/audit.py` names both in one place, which is also what
  decides which files the source audit reads and which need a provenance row.
- **A dead link inside a vendored record is worked around, never written over.** Eleven
  targets, over twenty-one of the four documents' 29 links, point out of this repository.
  Rewriting one would change bytes that are pinned by sha256, and that pin is the only
  thing letting a reader audit the copy against an original. So five targets are redirects
  and six are exclusions, all of them written down in `evidence/record/LINKS.md`, and
  `tests/test_vendored_record_links.py` fails if a link is neither resolvable nor accounted
  for.
- **No file names something a reader cannot reach.** No home directory, no unpublished
  repository, no ticket in a private tracker. `tests/test_source_audit.py` asserts it over
  every tracked text file — the manifest and the packaging metadata included, because the
  guard that came before it read Python only, and that is exactly how 55 private paths
  accumulated in a `.toml` file.
- **A missing input is a failure, not a skip.** There are no `skipif` guards on vendored
  inputs and no `importorskip`. A suite that shrinks quietly reports a number that means less
  than it looks like.
- **Attribution is owed to other people, not to other repositories of one's own.**
  `PROVENANCE.toml`'s `[[ported]]` rows used to name two unpublished repositories of this
  author's and a commit in each, and the published table's footer printed one of the commits.
  A reader could follow none of it, and there was nobody to attribute to: the code is this
  project's own and this repository is its published home. The integrity pin — the sha256,
  which is what the conformance suite and the footer both check — is what those rows are for,
  and it stays. Genuine third-party attribution is a different question and is intact and
  prominent: `upstream_repo` on the two DeformSplat sources, `attribution` on the sample
  asset, `THIRD_PARTY.md` for both.
- **Provenance is recorded; posture is not.** Nothing anywhere describes how this work is
  positioned relative to other work — that is not a fact about the artefact and does not
  belong in it.

## Open items

_None that anything here resolves: the repository reads nothing outside itself._ This
heading is about **resolution** — paths, imports, siblings — and not about every loose
end. One citation in `THIRD_PARTY.md` still carries a `VERIFY` flag on its venue; that
is attribution metadata a reader can check against the upstream project, not something
this repository resolves at run time.

The last external resolution went when the method came in. Three places had reached for a
sibling working tree: `tests/conftest.py`'s `sys.path` injection,
`tests/test_conformance.py`'s own resolve, and `scripts/build_table.py`'s `METHOD_REPO`
with the git-HEAD read behind it. All three are gone, and `plan1/provenance.py` no longer
contains a function capable of reading a sibling checkout at all — deleting `head_commit()`
is what makes that a fact rather than a claim. `tests/test_ported_method.py` parses every
module in the repository and fails on any string naming a sibling or any `parents[2]`
climb, so it cannot come back quietly.

The last external *reference* went afterwards, and it is a different thing from a
resolution: nothing was resolving those 55 paths, 4 private URLs and 27 ticket numbers, which
is precisely why they went unnoticed. `tests/test_source_audit.py` is the guard that now
covers references as well, over every tracked text file rather than over the modules alone.
