# plan1-comparison

Assembles the penguin ↔ DeformSplat baseline comparison from archived run records,
under rules pre-registered before any of it ran.

This repository is the **evidence chain behind one published table**, kept as a single
reviewable unit — and, since the method was ported in, the code that produced the
deformation as well. The pre-registration and the verdict that govern it are vendored
verbatim at `evidence/record/`; where copied code came from is recorded per file in
`evidence/PROVENANCE.toml`. Nothing here resolves anything outside this directory at
run time.

```
arap_core/            the ARAP solver and the 3DGS carry — ported, box C + D
box_b/edge_weights.py the B2 seam: (mode, magnitude) → per-edge weights
examples/             a runnable demonstration on a real 5.6 MB asset
evidence/             the run records, cluster sources and characterisation outputs
.                     the assembler, the manifest, the tests
```

**Nothing here resolves anything outside this directory.** No sibling working tree, no
absolute path off this repository, no `..`. That is asserted rather than claimed:
`tests/test_ported_method.py::test_no_file_in_the_repository_resolves_a_sibling_working_tree`
parses every module and fails on a string naming a sibling or a `parents[2]` climb.

## Verify it — the green gate

One command. It installs the repository, runs the whole suite, regenerates the published
table and diffs it against the committed copy, then rebuilds the §6.4 figure and diffs its
data record. Anything less than all five is not the claim being made.

```bash
git clone <url> plan1-comparison && cd plan1-comparison && python3 -m venv .venv && . .venv/bin/activate && ./scripts/verify.sh
```

Run on a fresh clone at a scratch path, in a fresh virtual environment, with no sibling
working trees present and nothing pre-installed, this reports **869 passed** and a clean
table diff. That count is asserted by `tests/test_suite_shape.py`, so a run that reported
fewer would fail rather than look like success.

**Read that number with its composition, not on its own.** 484 of the 869 — 56% — are
bookkeeping: the audits over this repository's own text, the vendored record checked
against what is on disk, the port's rows, the mutation record read back, the coverage
surface held to its rule. The other 385 test the method, the assembler, the figure and the
solver diagnostic. That ratio is not an accident or an embarrassment; it is what it costs
to make an artefact that can be checked by someone who does not trust it, and this
repository exists because an earlier one could not be. But a reader comparing this total
against a conventional project's is comparing two different things, and saying so here is
cheaper than letting them find out.

**The evidence travels with the repository.** Every number in the table resolves under
`evidence/`. It used to resolve out of a checkout elsewhere on the authoring machine, and
while it did, three test modules skipped silently on every other machine — 80 of 140 tests
— and the published table regenerated into something different without saying so.
`evidence/PROVENANCE.toml` records what each of the 49 copied files *is* and what it hashes
to, and asserts both in both directions: a file that changed fails, and so does one that
arrived with no row.

**Nothing here names anything you cannot reach.** No path on the author's machine, no
unpublished repository, no ticket in a private tracker. `tests/test_source_audit.py` asserts
that over every tracked text file — including the manifest, the packaging metadata and the
ignore rules, because the guard that came before it read Python only, and that is exactly how
55 private paths accumulated inside a `.toml` file while it watched the modules.

**The rules it was assembled under are in here too.** `evidence/record/` holds the
pre-registration and the verdict, which were cited sixteen times across this repository and
shipped zero times — including in the published table's own byline, which sent a reader to a
path they do not have. A citation that resolves nowhere is worse than none: it claims the
rules were fixed in advance while making the claim uncheckable.

Those two documents cite two companions of their own — the Phase-B probe verdict and the
feasibility addendum — and both are now vendored beside them, so those citations resolve too.
Twenty-one links across the four documents still point outward, at eleven distinct
targets, and none of them has been rewritten: every byte under `evidence/` is pinned by
sha256, and that pin is the only thing that lets a reader holding an original audit this
copy against it. They are classified instead — five targets as redirects, six as documents
that deliberately did not travel, with the reason for each — in
`evidence/record/LINKS.md`, and `tests/test_vendored_record_links.py` fails if any of the
29 links in the four is neither resolvable nor accounted for.

Note what the recorded archive dates do **not** say. Two are recorded, because one alone
reads backwards. `archive_date` is `2026-08-06` — the revision that travelled, which is
*after* the `2026-08-05` runs and would look like a rule written to fit them.
`archive_first_date` is when the pre-registration was added: `2026-08-05`, in the commit
that also carried the cluster handoff that dispatched those runs. Same day, not the day
after.

Neither is offered as proof, and same-day granularity could not provide it anyway.
Precedence is carried by a test instead:
`tests/test_saturation.py::test_archived_sweep_as_it_stands_is_not_saturated` applies the
pre-registered rule to the sweep as it stood when the rule was written and asserts **not
saturated, continue at ρ = 32**. The rule forced two further cluster runs before anything
could be published, and ρ = 64 turned the curve over. A rule that only ever agreed with what
was already there would be worth nothing; this one is on record disagreeing.

**The run logs carry the cluster account's identifiers** — a username, a hostname and
home-directory paths — and they are left in deliberately. `_logs/plan1_preflight_20260805.txt`
is the record of the preflight that recovered the baseline run and compared 6/6 source
hashes, and the file is pinned by sha256 like everything else under `evidence/`. Redacting
it would change those bytes and break the hash that makes the 6/6 checkable, which is the
only reason the file is worth shipping. No credentials, keys or tokens appear anywhere in
this repository.

## Can these tests fail?

A green suite says the tests ran. It does not say they constrain anything, and here the
two came apart at the worst available place: the comparison that selects the published
row could be changed from inclusive to exclusive and every test still passed. So could
the predicate that decides whether any row may be published at all. Coverage did not
predict it and in fact ran against it — **at the time that was measured**, the module with
the surviving mutants reported 100% line coverage while the module whose every mutant died
reported 86%. Both modules read 100% now, which is why the observation is dated rather
than restated in the present tense: it was evidence about the relationship between the two
measurements, not a standing fact about these files. The point it made survives intact. A
line can be executed and still constrain nothing, and that is the reason the coverage
number below is reported alongside a mutation score rather than instead of one.

`scripts/run_mutation.py` answers the question by measuring it: change one token in the
claim surface, run the whole suite, and see whether anything notices. It tokenises rather
than searching, so comments and docstrings are out of reach — a textual mutator produces
large numbers of "survivors" inside prose, and a record padded with those measures
nothing.

The result is committed at `mutation/mutation_record.json`: **132 of 135 killed** across
the assembler, the saturation rule, the readers, the manifest, the provenance loader and
the edge-weight seam, with the three survivors listed and argued for individually. All
three are equivalent mutants — a value read off a row the gate has already forced into
agreement, a loop walked backwards over a transitive relation, and the block size of a
file read.

Two of the 132 are marked as the weaker kind of kill, and separating them is the point:
those two mutants compiled but broke on import, so the suite never got as far as
asserting anything. They did not pass unnoticed, but they are evidence about the
interpreter rather than about the tests, and a score that folded them in would be the
more flattering of two readings presented as the only one. **130 were caught by an
assertion.**

`tests/test_mutation_record.py` reads the record back and fails if a survivor carries no
argument, if the source line it was found on has moved, or if any of the six targets no
longer hashes to what it hashed to when it was measured — so editing the claim surface
makes the record's staleness a test failure rather than something a reader has to
notice.

It is deliberately **not** in `./scripts/verify.sh`. The run takes about twenty minutes,
and a gate nobody waits for is not a gate.

## And how much of the code do they reach?

**100%**, on a declared surface, with branch coverage rather than line coverage.

The surface is `plan1`, `box_b`, `arap_core` and the worked example, declared in
`pyproject.toml` where the measurement actually reads it. `fail_under` is 100, so a gap
cannot open without someone deciding to open it, and
`tests/test_coverage_surface.py::test_the_declared_surface_is_the_one_this_repository_claims`
asserts the declaration against the claim — shrinking the surface is the cheapest way to
raise a percentage and it otherwise leaves no trace.

It was 90%, and almost all of the difference was **validation guards**: code whose only job
is to refuse bad input, and which had never once been shown refusing anything. A guard with
no test can be deleted by accident and leave the suite green; the failure it was written to
catch then arrives later, somewhere else, as an error naming nothing. `arap_core` alone had
four unexercised validators in `build_graph`, seven in the anchor check, and a
soft-constraint path that every call site in the repository declined to use.

Two lines on the surface are excluded, and **each carries its reason on the same line as
the marker**: an interval guard in the assembler that is unreachable while the invariant
above it holds, and the example's script entry point, which pytest imports rather than
executes. That rule is itself a test — a `# pragma: no cover` with nothing beside it fails,
and the rule is driven against one to show it can.

`scripts/`, `diagnostics/` and the mutation tool sit outside the surface, and the reason is
a positive one rather than an excuse. Everything that computes a published number is
covered by tests. Everything that *generates an artefact* is covered by
regenerate-and-diff: the gate rebuilds the comparison table and the figure's data record
from scratch and fails on a single differing byte, which constrains the output rather than
the path taken to it. The example is on the surface precisely because it is the one file
with neither — it computes no published number and generates nothing that gets diffed, so
"does it still run?" was genuinely unchecked, and this README quotes a number it printed.

Two things the record states rather than leaving to be inferred. **What was not mutated**
— rendering, the entry-point scripts, the solver diagnostic and the ported solver are out
of scope and the record names them, because an unqualified score invites a reader to take
a partial measurement for a total one. And **which tests are withheld from the kill
criterion**: `box_b/edge_weights.py` is pinned by sha256 and that hash is printed in the
published table's footer, so eight tests fail on any byte changing there before behaviour
enters into it. Counting those as kills would report a checksum as test strength — which
is exactly what an earlier exploratory run did, calling that module the strongest in the
repository while five of its mutants were in fact surviving, all of them inside
validation guards nothing drove. It now kills all twelve, and they are its own tests
doing it.

## The ported method

`arap_core/` (10 modules, 1,631 lines) and `box_b/edge_weights.py` (116 lines) are this
project's own, and this repository is their published home. Every file records what it is
and its sha256 under `[[ported]]` in `evidence/PROVENANCE.toml`, asserted in both
directions by `tests/test_ported_method.py` — 27 files, one row each. The reference rule's
hash is also what the published table's footer prints, so editing `box_b/edge_weights.py`
fails the conformance test, the footer check and the table build together.

`arap_core/` is 78 lines shorter than it was, and the deletion is worth naming because it
was the only dead code here. `cotangent_weights` computed mesh Laplacian weights, and this
repository has no mesh — the one asset is a point cloud, so nothing called it and nothing
could. It survived as long as it did by being cited: three separate pieces of prose used it
as the evidence that `build_graph`'s weight function is genuinely injected rather than
decorative. That evidence is now `box_b.edge_weights.make_scoped_weight_fn`, which is a
second weight function that actually exists, is actually injected, and is driven through a
full solve in `tests/method/test_edge_weights.py`.

Those rows used to name two unpublished repositories and a commit in each, and the footer
printed one of the commits. None of it could be followed by a reader, and there was nobody
to attribute to — so the citations are gone and the integrity pin, which is the part that
did the work, stays. Genuine third-party attribution is a different question and is intact:
see `THIRD_PARTY.md`.

**What deliberately stayed behind:** `box_b/descriptors.py`, `box_b/noise.py` and their 47
tests — the geometry reader. Nothing in the published table reads geometry, so it is out of
scope for an evidence chain behind that table, and a test asserts the two files are absent
rather than trusting that nobody copies them in later.

An earlier version of this note gave a different reason: that thickness is not a local
property on a surface shell, so the reader's premise fails on this asset. **That claim is
withdrawn.** It was measured with an estimator whose shrinking-ball iteration had a defect,
and the fixed estimator recovers analytic thickness on a clean synthetic shell. Why it still
does not recover it here is a separate result, and not one this repository carries.

Deform the sample asset — with zero displacement, this is the identity check that guards the
whole read → solve → carry → write chain:

```bash
python examples/run_penguin.py --ply data/penguin_original.ply --out /tmp/identity.ply --k 12 --gamma 50 --fixed-box -0.25 -0.25 -0.25 0.35 -0.10 0.15 --handle-box -0.25 0.25 -0.25 0.35 0.40 0.15 --disp 0 0 0
```

`data/penguin_original.ply` (5.6 MB, 23,548 Gaussians) is **tracked by exception** against
the `*.ply` ignore rule; the reason is recorded in `.gitignore` where a reader will meet it.

### The solver's evidence runs

The solver arrived here with nothing that drives it — no test touched `driver`,
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
and the two §6.2 figures. Results travel; the study code is cited rather than copied —
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

## The figure — a projection, not a render

Every figure this project had was a matplotlib plot of a characterisation grid, including
in the section that carries the contribution. A chapter about deforming a Gaussian splat
with no picture of a deformed Gaussian splat is a gap a reader notices immediately, and
the obvious sources were all closed: the nine cluster runs wrote **empty** `renders/`
directories, and the one render-looking figure that existed anywhere is also a plot *and* is
built on trex artifacts that did not travel — the trex **run records** are vendored here, its
renders and figures are not.

```bash
python scripts/make_projection_figure.py
```

`out/fig_64_penguin_projection.png` scatters the 23,548 Gaussian **means** through an
orthographic camera: original, deformed, and the deformed points coloured by how far each
travelled. That third panel is the one that carries the point — the handle region moves,
the pinned region is exactly still, and the interior varies smoothly between them.

**It is a projection and not a splat render**, and the figure says so on its own face
rather than only in a caption that will not travel with it. There is no rasteriser, no
opacity, no covariance and no view-dependent colour. It shows where the primitives went,
and nothing about what the scene would look like.

**What regenerates byte-identically, and what deliberately does not.** The figure's data
record does, and `scripts/verify.sh` diffs it. The PNG does **not**, and refusing to assert
it is the considered position: a matplotlib PNG's bytes depend on the matplotlib version,
on freetype and on platform font rasterisation, and pinning them would hand an examiner a
red suite for having a newer matplotlib. This project has already shipped one check that
passed only on the machine that wrote it — the solver diagnostic compared floats
bit-for-bit, and 20 of its 40 values move between BLAS backends. What is pinned instead is
the *drawn data*: each panel records the sha256 of its projected coordinates, and the
renderer refuses to draw anything that does not hash to it.

For the same reason the 19-second ARAP solve is not in the test path.
`out/penguin_deformed.ply` is committed and the solve is *recorded* — command, iterations,
convergence, energy — the same way the characterisation outputs are recorded rather than
regenerated. One number fell out of that which nothing was designed to produce: 3,593
primitives are exactly still, and `run_penguin.py` reported 3,593 fixed anchors. Those are
independent measurements, and a test asserts they agree.

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
| `arap_core/` | the ARAP solver and the 3DGS carry — boxes C and D |
| `box_b/edge_weights.py` | the B2 seam, and the conformance test's reference rule |
| `examples/run_penguin.py` | the runnable demonstration; `--disp 0 0 0` is the identity check |
| `tests/method/` | the method's own 129 tests in 9 modules, kept separate from the assembler's. 31 came with the port in 5 modules; the rest were added here — 6 when mutation found both of the edge-weight seam's validation guards undriven, and the remainder when the coverage work found the solver core's guards, both exits of its loop and its soft-constraint path undriven too |
| `diagnostics/` | the 40-rung solver ladder. `tests/test_diagnostic.py` **re-runs** it and compares all 40 records — it does not re-read the committed answer |
| `plan1/assemble.py` | **the seam** — manifest + records → validated table. Gating and gap arithmetic sit behind it |
| `plan1/saturation.py` | the pre-registered rule that selects the reported rigidity |
| `plan1/records.py` | the readers, and the precision model. Below the seam |
| `plan1/manifest.py` | the row-to-source binding |
| `plan1/render.py` | Markdown. Above the seam; decides nothing |
| `manifests/penguin_deformsplat.toml` | which run is which row, and what information each arm had |
| `evidence/` | the vendored run records, cluster sources and run logs — everything the table resolves |
| `evidence/characterisation/` | the characterisation study's outputs: the grids, the CSVs, the §6.2 figures and the three verdicts that certify them |
| `evidence/record/` | the pre-registration and the verdict that govern the table, plus the two companions they cite; `LINKS.md` says where each of their outward links goes |
| `evidence/PROVENANCE.toml` | what every copied file is, what it hashes to, and what deliberately did not travel |
| `tests/audit.py` | the repository-wide walk: what counts as a file here, and the three audits over it |
| `scripts/run_mutation.py` | the assertion-strength measurement — one token changed, the whole suite run. Not in the gate; it takes about twenty minutes |
| `mutation/mutation_record.json` | what it measured: the target set, the score, and every survivor with the reason it is acceptable |
| `tests/test_mutation_record.py` | reads that record back. Fails if a survivor carries no argument, or if the line it names has moved |
| `tests/test_coverage_surface.py` | the claim surface, read out of `pyproject.toml`, and the rule that every coverage marker on it carries a reason |
| `verified_environment.toml` | the exact versions the gate was last verified against. Documents; does not enforce, because a test asserting them would fail on every machine that is not this one |
| `.github/workflows/verify.yml` | the same five-step gate, run on Linux by a machine that is not the author's |
| `LICENSE` | MIT, and what it does **not** cover |
| `THIRD_PARTY.md` | the third-party material, its terms, and how the two modified files were changed |
| `third_party/deformsplat/` | the upstream Apache-2.0 text, and the complete diff of this project's 30 lines against it |
| `out/comparison_table.md` | the published table. Regenerates byte-identically; `tests/test_build_table.py` asserts it |
| `scripts/make_projection_figure.py` | the §6.4 figure — an orthographic projection of Gaussian means, **not** a splat render |
| `out/fig_64_penguin_projection.{png,json}` | that figure, and the display values it was drawn from |
| `out/penguin_deformed.ply` | the deformed asset the figure is drawn from, written by `run_penguin.py` |
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
retracted. What replaced it is in the suite:
`tests/test_integration.py::test_the_console_baseline_intervals_cover_the_parent_cells`
asserts the central fact, that every interval published under the console baseline overlaps
the cell a correction was claimed against.

**The reported row is selected by a rule declared in advance.** Smallest rigidity whose
PSNR falls within the replicate band of the sweep maximum; if the largest swept value is
still gaining more than the band, the curve has not saturated and *no row is published*.
With ρ = 32 and ρ = 64 run, the curve turned over and the rule returns **SATURATED**,
selecting ρ = 16.

## Status

**Complete.** The table publishes 63.6% / 72.6% / 80.4% at ρ = 16, and every number traces
to a named run. Those three are fractions of a gap, so the values they are fractions *of* are
here rather than only in `out/comparison_table.md` — the two endpoints and the selected row,
per metric, each at the precision its own source recorded:

| metric | none (grouping off, unit rigidity) | imposed, ρ = 16 | inferred groups (baseline, as published) | gap closed |
|---|---|---|---|---|
| PSNR | 19.277 | 22.953 | 25.055 | 63.6% |
| SSIM | 0.9199 | 0.9443 | 0.9535 | 72.6% |
| LPIPS | 0.0916 | 0.0634 | 0.0565 | 80.4% |

**LPIPS falls where the other two rise, and no column has to be inverted mentally.** The
fraction is (row − null) / (baseline − null) on all three, so inverting a metric flips
numerator and denominator together and *more recovered* already means the same thing in every
row. The column heads are the published table's own row labels, so a row here can be found
there — with the frame that table carries in a column of its own: the baseline observes the
object's motion and this method does not, so exceeding it is neither a goal nor a claim.

**These cells are not typed in either.**
`tests/test_build_table.py::test_the_readme_publishes_the_absolute_values_the_assembler_produces`
re-assembles the table from the manifest and the run records and asserts every one of them —
heads included — against what comes out, through the same formatters the published table
prints with. Same reason as the verdict counts above: a number is published where a reader
lands, so that is where it has to be checked.

Both halves of the wiring gate pass. The conformance test: the deployed cluster rule and
the method repository's tested reference agree edge-for-edge across ρ = 0.0625…64,
boundary-crossing edges are untouched by both, and four negative controls confirm the check
can fail. The in-run assertion: it did not fire on either saturation run, and
`tests/test_wiring_assertion.py` establishes that it *could* have — silent on the correct
rule, firing on five injected faults, with each fault attributed to the arm that caught it.

The one thing it cannot catch is a label-frame mismatch, and no harness can make it: the
caller derives its rigid-interior mask from the same label array it passes to the rule. That
is recorded rather than hidden — `evidence/record/plan1_verdict.md` §1 states it, and closes
it by construction.

## Licence and attribution

This repository is **MIT** — see `LICENSE`. That covers the work authored here and nothing
else, because two things here are not this project's.

**The two cluster sources under `evidence/cluster/` are DeformSplat's**
(`github.com/vision3d-lab/deformsplat` @ `60955d67`, Apache-2.0), 1,581 lines, and both
carry a local modification. Apache-2.0 asks that a modified file say so, and neither can:
both are pinned by sha256, the manifest cites one of the hashes, and two suites parse them
by AST — a licence header in either would break all of that and stop the copy being what
actually ran. So the notice sits beside the file instead, and goes further than the licence
asks: `third_party/deformsplat/` commits the **complete diff**, 30 lines across the two,
applying cleanly to the pinned commit. That diff is also the evidence for the strongest
claim this project makes about its own footprint — **the ARAP formulation, the LBS, the
solver and the optimiser are untouched.** `tests/test_upstream_diff.py` keeps the diffs from
drifting away from the files they describe.

**The sample asset derives from DiVa360** (`github.com/brown-ivl/DiVa360`, CVPR 2024, MIT).
`data/penguin_original.ply` is a 3DGS export of a checkpoint trained on its `penguin`
sequence — and that checkpoint came with the cluster image rather than being trained here.
`THIRD_PARTY.md` carries both attributions in full.
