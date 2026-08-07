# Plan 1 — imposed rigidity against the DeformSplat baseline — VERDICT

_Authored 2026-08-06, after execution. Rules pre-registered in [plan1_prereg.md](plan1_prereg.md)
before any run; how each declared branch resolved is in its §10. The table this verdict interprets
regenerates from a manifest — `~/plan1-comparison/out/comparison_table.md` — and no number below is
retyped from anywhere else._

---

## 1. The gate, first

[plan1_prereg.md](plan1_prereg.md) §6 makes the wiring gate **hard**: if either check fails, no
outcome is claimed on the comparison in any form. It is stated here before any comparison claim
because that is what it is — a precondition, not a footnote. This project has previously carried a
mechanism that was certified *live* but not *correctly wired*, and published nothing on it.

**Both checks pass.**

- **The conformance test** drives the method repository's tested edge-weight rule and the cluster's
  deployed rule over the same graph and requires agreement edge-for-edge, at ρ = 0.0625 … 64. The
  primary comparison is at ρ ≠ 1 deliberately: that is the branch the known failure modes live in.
  It carries four negative controls, so it is a check that can fail.
- **The in-run assertion** rode both saturation runs and **did not fire**. Neither log carries an
  `AssertionError`; both reached step 501 and wrote statistics.

Preflight confirmed the sweep sources were unchanged since the archived runs — **6/6 sha256 MATCH**
— so under §6.1 the wiring evidence transfers to the archived rows and no drift limitation is owed.

### 1.1 The assertion's silence is evidence, and here is why

An assertion that *cannot* fire is silent too. This project retracted exactly such an assertion on
2026-07-29: the earlier in-code check read `torch.equal(weight, rho_scale_weights(weight, …, 1.0))`
and the rule early-returns at ρ = 1, so it evaluated `torch.equal(weight, weight)` and fired
without error on every run — as it would have with a completely broken scaling path.

The replacement probes at ρ = 2, fixed independently of the run's own ρ. It is now driven against
deliberately broken rules by `tests/test_wiring_assertion.py`, with faults injected **at the rule**
— the only place the block can observe one:

| injected at the rule | outcome |
|---|---|
| the archived rule, unmodified | **silent** — the check is not vacuous |
| renormalises after scaling | fires `T0.1b` |
| gathers neighbour labels through a wrong index | fires `T0.1b` |
| reads the wrong rigid-region id | fires `T0.1b` |
| mis-scales the rigid interior | fires `T0.1c` |
| rigid interior is empty | fires `T0.1a` |
| label frame permuted on both sides | **silent** |

Every arm of the block catches something, so none is carried as dead weight. The harness is bound
to the archived source by a drift guard: every condition it transcribes must appear verbatim in
[`cluster/sources_20260805_patched/deform_splat.py`](../../cluster/sources_20260805_patched/deform_splat.py),
which is archived byte-exact and hashes to the value the manifest cites.

### 1.2 Three failure modes, three different kinds of argument

The gate named three failure modes. They are **not** all closed the same way, and reading one as
the other would overstate the result. Which is which:

| failure mode | closed by | strength |
|---|---|---|
| renormalisation after scaling | **experiment** — injected, fires `T0.1b` | measured |
| a mis-gathered neighbour index | **experiment** — injected, fires `T0.1b` | measured |
| a label-frame mismatch | **construction** — code inspection | argued, not measured |

**The label frame is closed by construction, and that is code inspection rather than measurement.**
It is labelled as such here, consistently with how the null-row equivalence is already labelled in
the table's own limitations. The argument: the edge weights, the neighbour adjacency and the region
label all derive from the same `anchor` tensor inside one gradient-free block, so no second ordering
exists to mismatch. The caller derives its rigid-interior mask from the same `_rl` array it passes
down to the rule — permute that array and both sides move together. It follows that **no harness can
make a label-frame mismatch fire this assertion**; the acceptance criterion demanding such a
demonstration was unsatisfiable in principle and is amended on its ticket rather than quietly
dropped. What the block does deliver in that territory is `T0.1a`: the rigid interior is non-empty.

**On the ordering.** The reachability demonstration is retrospective — the runs were done first.
That is weaker than demonstrating it beforehand, but not in the way a post-hoc threshold is weaker,
and the distinction matters because this project has recorded a genuine threshold reversal before
and the two must not be conflated. A threshold chosen after seeing data can be chosen favourably.
An assertion either can fire or cannot, and that is fixed by its code; proving it later does not
change what it did on the node.

### 1.3 The out-of-scope check

**The cluster-side pass-through wrapper** — `sweep_rho.py`, and the `deform_splat.py` call site that
hands `weight` to the rule — is **not** covered by any local suite. It needs the node, the container
image and a GPU. Keeping it logic-free is the mitigation; a green local run is not evidence about
it. A reader should not read one as the other.

---

## 2. The claim

With the gate met, the comparison may be stated. The claim is narrow and the narrowness is the
point:

> **Rigidity can be imposed continuously on stated regions, and doing so recovers a substantial
> fraction of the benefit the DeformSplat baseline extracts from observed motion — 63.6% on PSNR,
> 72.6% on SSIM, 80.4% on LPIPS — at the setting the pre-registered rule selects (ρ = 16), on one
> asset.**

**What this is not.** It is *not* evidence that rigidity is geometrically legible — readable off a
static asset. Nothing here tests that. The regions here come from a distance-to-handle rule, and
imposing rigidity on stated regions must never be blurred into reading rigidity off geometry.

**The baseline is not a competitor.** It observes the object's motion; this method does not.
Exceeding it on reconstruction fidelity is not a goal, is not claimed, and is not the frame. The
information asymmetry is the frame, which is why it travels as a column of the table rather than as
prose.

### 2.1 The asymmetry is verifiable in the source, not merely asserted

The rigidity field is derived by one call:

```python
_rl = partition_anchors_by_handle(anchor, points_3d_filtered.mean(0), getattr(self.cfg, 'rho_frac', 0.3))
```

It reads the **anchor set** and the mean of the **authored drag source** only.
`drag_target_filtered` — the observed motion, which is what the baseline is given — exists in the
same scope and never reaches it. So the rigidity field never sees the motion. This is asserted
against the archived text by `test_the_partition_never_reads_the_drag_target`, so it is checkable
rather than stated.

### 2.2 Which row is reported, and why that one

The reported setting is chosen by the pre-registered rule, applied by **running the selector**, not
by eye. The two saturation runs extended the sweep past its endpoint and the curve turned over:

| ρ | PSNR |
|---|---|
| 0.25 | 17.9064 |
| 4 | 22.1045 |
| 16 | **22.9534** |
| 32 | 21.8276 |
| 64 | 20.7387 |

The last gain is −1.0889 dB: the curve has **turned over**, which satisfies the rule's
`last_gain ≤ band` test against the 0.0841 dB replicate band, so it returns **SATURATED**. The
smallest rigidity within the band of the maximum is **ρ = 16**. (A fall is not a gain, and the
verdict sentence the selector emits says so; the wording change is disclosed with its diff in
[plan1_prereg.md](plan1_prereg.md) §10.6.) Taking the smallest qualifying
rigidity rather than the argmax is what stops an over-stiffened tail ever being reported as the best
setting. The full sweep is published beneath the table: the selection is disclosed, not hidden.

### 2.3 Why one published cell differs from the parent spec's

The parent spec published 63.6% / 72.6% / **79.2%**; this table publishes 63.6% / 72.6% / **80.4%**.
The LPIPS cell moved because the **input sharpened**, not because a different run was read.
Preflight recovered the baseline run's own full-precision statistics record, so the row is bound to
that record instead of to a console line at three decimals, and every fraction became exact.

Two things follow, and both matter to a reader checking this table against that one:

- **The parent's cells were never wrong.** Rounding every input to display precision and then
  dividing reproduces all three exactly (63.6206%, 72.619%, 79.2135%). The route is loose; the
  answers were not.
- **An earlier claim that Plan 1 *corrected* the parent's SSIM cell to 72.5% is retracted.** Under
  the console baseline the assembler's own interval was [72.3880%, 72.6037%], which contains the
  parent's 72.6%. A point estimate had been compared against a published cell while an interval
  covering that cell was in hand. All three console-baseline intervals contained the values later
  recovered at full precision. The retraction is in
  [`docs/specs/plan-1-comparison-assembly-spec.md`](../../docs/specs/plan-1-comparison-assembly-spec.md).

The parent spec's instruction to reproduce its three cells exactly, treating a mismatch as evidence
of reading the wrong runs, is **superseded**. It answered an input-identity question by testing
outputs, which only works if inputs never sharpen — and §7 declared in advance that they might. The
comparability gate answers the same question directly, keying on the step-0 metric triple, the
primitive count and the evaluation step; it would catch a swapped run that happened to produce
similar cells, which output-matching would not. All nine rows pass it.

---

## 3. Limitations, at the point of the claim

Stated here so an examiner does not have to hunt for what this result does not establish.

- **Single asset, single evaluation camera, single seed per setting.** Nothing here establishes that
  the result generalises to another object.
- **The no-rigidity row is the mechanism-off run alone.** Its equivalence to the unit-rigidity runs
  rests on **code inspection** — the scaling helper early-returns its input at ρ = 1 — and not on
  measurement: the gate that would have established it end to end is the one that failed.
- **The replicate band was measured at unit rigidity.** Applying it across the sweep assumes
  replicate noise does not grow with rigidity. That is an assumption, not a measurement.
- **The label frame is closed by construction, not by measurement** (§1.2). Establishing it by
  measurement would need the node and a region-label array that was never archived, and the gate
  does not depend on it.
- **The pass-through wrapper is untested locally** (§1.3).
- **The baseline observes the object's motion; this method does not.** Exceeding it on
  reconstruction fidelity is not a goal and is not claimed.
- **Regions here are geometric, not authored labels.** Region-labelled imposed rigidity keeps the
  priority and preconditions the parent spec assigns it; it is not part of this result.

## 4. What the record rests on

| claim | where it is checkable |
|---|---|
| sources unchanged, so evidence transfers | [`plan1_preflight_20260805.txt`](../../cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt) §1a; [feasibility addendum](plan1_feasibility_addendum.md) §1 |
| the assertion could have fired | `tests/test_wiring_assertion.py`, bound to the archived source by a drift guard |
| the call site that ran ρ = 32/64 | [`cluster/sources_20260805_patched/`](../../cluster/sources_20260805_patched), sha256 `e2ca10cf…`, recorded inline in both run logs |
| the rule matches its tested reference | `tests/test_conformance.py`, four negative controls |
| the rows began from the same state | the comparability gate, all nine rows, full precision |
| the reported row was selected by rule | `plan1.saturation`, run rather than read off |
| every published number traces to a run | `manifests/penguin_deformsplat.toml` → `out/comparison_table.md` |
| nothing deviated from the pre-registration | [plan1_prereg.md](plan1_prereg.md) §9, with §10 recording how each branch resolved |
