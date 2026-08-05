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

Six archived runs hold the imposed-rigidity arm as structured statistics; the baseline
row exists only as a line of console output. Reading numbers off seven files and typing
them into a chapter repeats the transcription risk on every re-run, checks nothing about
whether the rows are comparable, and leaves a reader no way to trace a published number
back to the run that produced it.

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

## The three things this enforces

**Rows must demonstrably have begun from the same state.** The gate is the step-0 metric
triple, the primitive count and the evaluation step — not a recorded checkpoint path,
because a path is a string that may have been overwritten between runs. Failure raises; it
never warns. A silently-wrong comparison produces plausible numbers, which is the worst
outcome available.

**No number is printed at a precision its source does not have.** The baseline is a
console line at three decimals of PSNR. Every fraction derived from it carries the
resulting rounding interval — on LPIPS that is worth about two percentage points, so it is
stated rather than absorbed.

**The reported row is selected by a rule declared in advance.** Smallest rigidity whose
PSNR falls within the replicate band of the sweep maximum; if the largest swept value is
still gaining more than the band, the curve has not saturated and *no row is published*.
As of the archived sweep the rule returns **NOT SATURATED** — which is what makes the
ρ = 32 and ρ = 64 runs a requirement rather than a nicety.

## Status

The local half of the wiring gate **passes**: the deployed cluster rule and the method
repository's tested reference agree edge-for-edge across ρ = 0.0625…64, boundary-crossing
edges are untouched by both, and four negative controls confirm the check can fail.

Outstanding, and both need the cluster: the ρ = 32 / ρ = 64 saturation runs carrying the
non-tautological in-run assertion, and a preflight pass confirming the node's sources still
match the archived hashes. Until the sweep saturates, the assembler publishes no
gap-recovered fraction.
