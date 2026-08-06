# CONTEXT — plan1-comparison

_The single-context orientation doc for this repository. Read this before changing anything._

## What this repository is

**The escape plan.** One published comparison table, and the whole evidence chain behind it,
kept as a single reviewable unit that a examiner can clone and check.

The test every decision here is measured against:

> *Does a bare clone, on a machine that has never seen the other two repositories, reproduce
> what the dissertation claims?*

If tomorrow were the deadline, this repository plus its write-up is a complete submission.
That is not an aspiration about code quality — it is a load-bearing constraint, and most of
what looks unusual here follows from it.

## The three repositories

| repo | role | shipped? |
|---|---|---|
| `llamsumn/3D-arap` (`~/3D`) | the archive. Record and planning: specs, pre-registration, verdicts, the characterisation study's code, run logs. The lab notebook. | no |
| `arap-deform-3dgs` | the **method** — the four-box deformation system, and the risky novelty (geometry-derived regions) that may never land. | separately |
| **`plan1-comparison`** (here) | **the escape plan.** Self-sufficient. Depends on neither of the others at run time. | **yes** |

The split exists because the three have different failure modes. The archive is allowed to
be messy and is allowed to record things that were later retracted — that is what a lab
notebook is for. The method repository is allowed to carry work in progress and paused
tracks. This repository is allowed neither: everything in it must be true, checkable, and
resolvable without leaving it.

## The vendoring discipline

Everything this repository reads at run time is under `evidence/`, and every byte of it is
recorded in `evidence/PROVENANCE.toml` — source path, sha256, and why it travelled. Derived
artefacts additionally record the command that produced them, the date, and the verdict that
certifies them.

The record is asserted **in both directions**, by `tests/test_vendored_evidence.py`:

- a recorded file that no longer hashes to its recorded value **fails**, and
- a file that arrived under `evidence/` with no row **fails just as loudly**.

The second direction is the one that is easy to omit and does most of the work. A
one-directional check lets evidence accumulate quietly, unrecorded and unexplained — which
is the state this repository exists to escape from.

### Why a copy and not a live binding — the trade, stated

**Vendoring gives up divergence detection.** A copy cannot notice that its original changed.
This was traded away deliberately, for self-containment, and the reason is specific to Plan 1
rather than general:

> Divergence detection protects a **living** codebase — it tells you that something you still
> depend on has moved underneath you. **Plan 1 is frozen.** Its evidence is nine archived runs
> that will never be re-run, a deployed cluster source fixed at a cited hash, and a reference
> rule as it stood at the commit that produced the evidence. "Notice if upstream moves"
> protects nothing about that claim, because nothing upstream moving could make the claim
> more or less true. Self-containment, by contrast, is exactly what an examiner needs and
> exactly what this repository previously did not have.

Without that paragraph a reader reads the vendored copy as an oversight. It is not; it is the
decision, and `PROVENANCE.toml` is what keeps it honest — anyone still holding an original can
audit every copied byte against it.

**The cost is real and is stated rather than hidden.** If the archive's copy of a run record
were edited tomorrow, nothing here would report it. What is defended instead is that the copy
is identifiable: a reader can always tell *which* bytes this table was built from.

## What is deliberately excluded

| not here | why |
|---|---|
| `box_b/descriptors.py`, `box_b/noise.py` and their 47 tests | the geometry reader. Paused on a diagnosed shrinking-ball defect — this is the risk the escape plan exists to be safe from. The B2 seam (`box_b/edge_weights.py`) is complete and standing, and it is the only part that travels. |
| boxes A and B of the method | not built. This repository ships what is validated. |
| the characterisation study's **code** | results travel, code is cited. Its outputs are under `evidence/characterisation/` with the command that wrote each one; forking a living study into a frozen artifact would hand a reader two versions to reconcile. |
| a second asset's (trex) sweep, ~1.4 MB | no manifest row binds it, no published number derives from it. Recorded as an exclusion with a reason, not silently absent. |
| the specs, pre-registration and verdicts | they live in the archive by two-repo discipline. Cited from here, never copied. |

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
   interval to interval. This repository once shipped a "correction" that came from ignoring
   that, and it is retracted in the archive's assembly spec.
3. **The reported row is selected by a rule declared in advance** — smallest rigidity whose
   PSNR falls within the replicate band of the sweep maximum, or no row is published at all.

## Conventions

- **`out/comparison_table.md` is generated, never hand-edited.** It regenerates
  byte-identically and `tests/test_build_table.py` asserts exactly that. Adding a run is a
  manifest edit; no number is ever retyped.
- **Nothing under `evidence/` is edited.** Copying is not editing; anything else breaks the
  hash that makes the copy auditable.
- **A missing input is a failure, not a skip.** There are no `skipif` guards on vendored
  inputs and no `importorskip`. A suite that shrinks quietly reports a number that means less
  than it looks like, which is the specific failure this repository was built to close.

## Open items

_None. The repository resolves nothing outside itself._

The last external resolution went with [#16](https://github.com/llamsumn/3D-arap/issues/16),
which ported the method. Three places had reached for a sibling `../arap-deform-3dgs`:
`tests/conftest.py`'s `sys.path` injection, `tests/test_conformance.py`'s own resolve, and
`scripts/build_table.py`'s `METHOD_REPO` with the git-HEAD read behind it. All three are
gone, and `plan1/provenance.py` no longer contains a function capable of reading a sibling
checkout at all — deleting `head_commit()` is what makes that a fact rather than a claim.
`tests/test_ported_method.py` parses every module in the repository and fails on any string
naming a sibling or any `parents[2]` climb, so it cannot come back quietly.
