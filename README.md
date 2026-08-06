# plan1-comparison

Assembles the penguin ↔ DeformSplat baseline comparison from archived run records,
under rules pre-registered before any of it ran.

This repository is the **evidence chain behind one published table**, kept as a single
reviewable unit — and, since the method was ported in, the code that produced the
deformation as well. The planning record (specs, pre-registration, verdicts) lives in the
`llamsumn/3D-arap` archive; the ongoing method development continues in `arap-deform-3dgs`,
which this repository no longer depends on at run time.

```
arap_core/            the ARAP solver and the 3DGS carry — ported, box C + D
box_b/edge_weights.py the B2 seam: (mode, magnitude) → per-edge weights
examples/             a runnable demonstration on a real 5.6 MB asset
evidence/             the run records, cluster sources and characterisation outputs
.                     the assembler, the manifest, the tests
```

**Nothing here resolves anything outside this directory.** No sibling working tree, no
`~/3D`, no `..`. That is asserted rather than claimed:
`tests/test_ported_method.py::test_no_file_in_the_repository_resolves_a_sibling_working_tree`
parses every module and fails on a string naming a sibling or a `parents[2]` climb.

## Verify it — the green gate

One command. It installs the repository, runs the whole suite, regenerates the published
table and diffs it against the committed copy. Anything less than all four is not the claim
being made.

```bash
git clone <url> plan1-comparison && cd plan1-comparison && python3 -m venv .venv && . .venv/bin/activate && ./scripts/verify.sh
```

Run on a fresh clone at a scratch path, in a fresh virtual environment, with no sibling
working trees present and nothing pre-installed, this reports **419 passed** and a clean
table diff. That count is asserted by `tests/test_suite_shape.py`, so a run that reported
fewer would fail rather than look like success.

**The evidence travels with the repository.** Every number in the table resolves under
`evidence/`, which used to be a sibling `~/3D` checkout. While it was, three test modules
skipped silently on any other machine — 80 of 140 tests — and the published table
regenerated into something different without saying so. `evidence/PROVENANCE.toml` records
the source path and sha256 of all 45 copied files, and asserts them in both directions:
a file that changed fails, and so does one that arrived with no row.

## The ported method

`arap_core/` (10 modules, 1,709 lines) and `box_b/edge_weights.py` (116 lines) come from
`arap-deform-3dgs@ede5fd3`. Every ported file records its source repository, source commit
and sha256 under `[[ported]]` in `evidence/PROVENANCE.toml`, asserted in both directions by
`tests/test_ported_method.py` — 23 files, one row each, 19 from the method repository and 4
from the archive with the solver diagnostic. The reference rule's hash is also
what the published table's footer prints, so editing `box_b/edge_weights.py` fails the
conformance test, the footer check and the table build together.

**What deliberately stayed behind:** `box_b/descriptors.py`, `box_b/noise.py` and their 47
tests — the geometry reader, paused on a diagnosed shrinking-ball defect. On the penguin,
which is a surface shell, thickness is not a local property, so the estimator's premise does
not hold there. That is the risk this repository exists to be safe from, and a test asserts
the two files are absent rather than trusting that nobody copies them in later.

Deform the sample asset — with zero displacement, this is the identity check that guards the
whole read → solve → carry → write chain:

```bash
python examples/run_penguin.py --ply data/penguin_original.ply --out /tmp/identity.ply --k 12 --gamma 50 --fixed-box -0.25 -0.25 -0.25 0.35 -0.10 0.15 --handle-box -0.25 0.25 -0.25 0.35 0.40 0.15 --disp 0 0 0
```

`data/penguin_original.ply` (5.6 MB, 23,548 Gaussians) is **tracked by exception** against
the `*.ply` ignore rule; the reason is recorded in `.gitignore` where a reader will meet it.

### The solver's evidence runs

`arap-deform-3dgs`'s own suite never drives the solver — no test there touches `driver`,
`global_step` or `local_step`. `diagnostics/` carries the 40-rung ladder that does, and
`tests/test_diagnostic.py` **re-executes** all six phases and compares every record against
`diagnostics/arap_core_diagnostic.json`, field by field. It does not compare the committed
JSON against itself; that tautology is the failure mode this project has shipped twice, and
a test traces the interpreter into all three solver modules to prove they were reached.

Re-executing rather than re-reading found something on the first run. 39 of the 40 records
reproduced bit-for-bit against the ported core; `G5` did not. It asserted that SH bands 1 and
above are *left untouched* — a correct boundary check on the DC-only stub it was written for
in July, and obsolete since B1 replaced that stub with real Wigner-D. `G5` is rewritten to
ask the question the real implementation has, and both the rewrite and the regenerated record
are documented in `evidence/PROVENANCE.toml`. Runtime is ~2 s, so it sits in the default
suite rather than behind a marker.

## The characterisation evidence

`evidence/characterisation/` holds the study that motivated a *predicted* rigidity field
rather than a hand-tuned one: the K × γ grid, the ρ × δ mask grid, the R-swing diagnostic,
and the two §6.2 figures. Results travel; the study code stays in `~/3D` and is cited —
every vendored file records the command that wrote it, the date, and the verdict certifying
it.

Three verdicts certify the set, and **none of it is regenerated** — they assert against
these exact bytes:

| verdict | result | what it checks |
|---|---|---|
| `item1_kgamma/KGAMMA_VERDICT.md` | **11/11 pass** | K is inert and γ flat in the live band — scope is not reliably hand-tunable through the KNN graph |
| `item2_mask/MASK_VERDICT.md` | **17/17 pass** | ρ responds on both panels; box B therefore predicts a *per-region* field. The pin reading is split across panels, so the mechanism claim is earned only where it holds |
| `reporting/FIGURE_CHECK.md` | **9/9 pass, 0 misrepresentations over 100 aggregate cells** | every plotted value re-derived from its source CSV |

`tests/test_vendored_evidence.py` reads those three counts back out of the verdict files, so
this table cannot drift away from what it describes, and pins the five cited CSVs at their
row counts — a truncated copy is caught as a wrong number rather than shipped as a right one.

## Why the table is not just typed out

Nine archived runs feed the table. Reading numbers off nine files and typing them into a
chapter repeats the transcription risk on every re-run, checks nothing about whether the
rows are comparable, and leaves a reader no way to trace a published number back to the
run that produced it.

So: **one assembler**, a pure function from a declared manifest plus the run records to a
validated comparison table. Adding a run is a manifest edit, never a retyped number.

## Run it

```bash
pip install -e ".[test]"
```

```bash
python -m pytest
```

```bash
python scripts/build_table.py
```

The assembler and the saturation rule are still pure stdlib — the whole decision surface is
testable on CPU with no GPU and no network. `numpy`, `scipy` and `plyfile` arrived with the
ported method and are declared runtime dependencies; `torch` is what the deployed cluster
rule is written in, and it is a **hard** test dependency rather than an optional extra,
because the two modules that need it are the wiring gate.

There are no `skipif` guards on vendored inputs and no `importorskip`. A missing input or a
missing `torch` makes the suite **error**, not shrink.

## What is where

| path | role |
|---|---|
| `arap_core/` | the ARAP solver and the 3DGS carry — boxes C and D, ported from `arap-deform-3dgs@ede5fd3` |
| `box_b/edge_weights.py` | the B2 seam, and the conformance test's reference rule |
| `examples/run_penguin.py` | the runnable demonstration; `--disp 0 0 0` is the identity check |
| `tests/method/` | the 31 ported method tests, kept separate from the assembler's |
| `diagnostics/` | the 40-rung solver ladder. `tests/test_diagnostic.py` **re-runs** it and compares all 40 records — it does not re-read the committed answer |
| `plan1/assemble.py` | **the seam** — manifest + records → validated table. Gating and gap arithmetic sit behind it |
| `plan1/saturation.py` | the pre-registered rule that selects the reported rigidity |
| `plan1/records.py` | the readers, and the precision model. Below the seam |
| `plan1/manifest.py` | the row-to-source binding |
| `plan1/render.py` | Markdown. Above the seam; decides nothing |
| `manifests/penguin_deformsplat.toml` | which run is which row, and what information each arm had |
| `evidence/` | the vendored run records, cluster sources and run logs — everything the table resolves |
| `evidence/characterisation/` | the characterisation study's outputs: the grids, the CSVs, the §6.2 figures and the three verdicts that certify them |
| `evidence/PROVENANCE.toml` | where every copied file came from, what it hashes to, and what deliberately did not travel |
| `out/comparison_table.md` | the published table. Regenerates byte-identically; `tests/test_build_table.py` asserts it |
| `tests/test_conformance.py` | does the **deployed** rigidity rule match the **tested** reference? |
| `tests/test_wiring_assertion.py` | is the in-run assertion's **silence** evidence? Drives it against broken rules |

## The three things this enforces

**Rows must demonstrably have begun from the same state.** The gate is the step-0 metric
triple, the primitive count and the evaluation step — not a recorded checkpoint path,
because a path is a string that may have been overwritten between runs. Failure raises; it
never warns. A silently-wrong comparison produces plausible numbers, which is the worst
outcome available.

**No number is printed at a precision its source does not have.** The baseline was
originally a console line at three decimals of PSNR, and every fraction derived from it
carried the resulting rounding interval — on LPIPS that was worth about two percentage
points. Preflight recovered that run's own full-precision record, so the published cells
are now exact; the console-line world is kept as a live fixture in the integration suite,
because it is the branch the pre-registration declared and because a coarse source is the
only thing that exercises the interval arithmetic.

A published cell printed at coarser precision denotes an interval too, so a comparison
against one is made **interval to interval**. Comparing it as a point manufactures
corrections that the evidence does not license — this repository shipped one, and it is
retracted in the archive's assembly spec.

**The reported row is selected by a rule declared in advance.** Smallest rigidity whose
PSNR falls within the replicate band of the sweep maximum; if the largest swept value is
still gaining more than the band, the curve has not saturated and *no row is published*.
With ρ = 32 and ρ = 64 run, the curve turned over and the rule returns **SATURATED**,
selecting ρ = 16.

## Status

**Complete.** The table publishes 63.6% / 72.6% / 80.4% at ρ = 16, and every number traces
to a named run.

Both halves of the wiring gate pass. The conformance test: the deployed cluster rule and
the method repository's tested reference agree edge-for-edge across ρ = 0.0625…64,
boundary-crossing edges are untouched by both, and four negative controls confirm the check
can fail. The in-run assertion: it did not fire on either saturation run, and
`tests/test_wiring_assertion.py` establishes that it *could* have — silent on the correct
rule, firing on five injected faults, with each fault attributed to the arm that caught it.

The one thing it cannot catch is a label-frame mismatch, and no harness can make it: the
caller derives its rigid-interior mask from the same label array it passes to the rule. That
is recorded rather than hidden, and closed by construction in the archive's verdict.
