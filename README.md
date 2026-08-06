# plan1-comparison

Assembles the penguin ↔ DeformSplat baseline comparison from archived run records,
under rules pre-registered before any of it ran.

This repository is the **evidence chain behind one published table**, kept as a single
reviewable unit. It is not the method — the deformation system lives in
[`arap-deform-3dgs`](../arap-deform-3dgs), which this repo consumes as a dependency and
never modifies. The research record (spec, pre-registration, run evidence, cluster
sources) lives in the `llamsumn/3D-arap` archive.

```
../arap-deform-3dgs   the method   — supplies the reference edge-weight rule
../3D                 the archive  — supplies the run records and the spec
.                     this repo    — the assembler, the manifest, the tests
```

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
