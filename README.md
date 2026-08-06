# plan1-comparison

Assembles the penguin ↔ DeformSplat baseline comparison from archived run records,
under rules pre-registered before any of it ran.

This repository is the **evidence chain behind one published table**, kept as a single
reviewable unit. It is not the method — the deformation system lives in
[`arap-deform-3dgs`](../arap-deform-3dgs), which this repo consumes as a dependency and
never modifies. The planning record (specs, pre-registration, verdicts) lives in the
`llamsumn/3D-arap` archive.

```
evidence/             the run records and archived cluster sources, vendored
../arap-deform-3dgs   the method   — supplies the reference edge-weight rule
.                     this repo    — the assembler, the manifest, the tests
```

**The evidence travels with the repository.** Every number in the table resolves under
`evidence/`, which used to be a sibling `~/3D` checkout. While it was, three test modules
skipped silently on any other machine — 80 of 140 tests — and the published table
regenerated into something different without saying so. `evidence/PROVENANCE.toml` records
the source path and sha256 of all 45 copied files, and asserts them in both directions:
a file that changed fails, and so does one that arrived with no row.

The reference edge-weight rule is still resolved from `../arap-deform-3dgs`; porting it is
the one remaining external dependency.

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
python scripts/build_table.py
```

```bash
python -m pytest
```

The assembler and the saturation rule are pure stdlib — the whole decision surface is
testable on CPU with no asset file, no GPU and no network. `numpy` and `torch` are needed
only by the conformance test.

To bind the conformance test to the method repo by install rather than by path fallback:

```bash
pip install -e ../arap-deform-3dgs
```

## What is where

| path | role |
|---|---|
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
