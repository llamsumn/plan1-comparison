# Plan 1 — PRE-REGISTRATION (rules declared before preflight and before any run)

_Authored 2026-08-05, **before** the preflight pass, before the assembler was written, and before
the saturation runs were launched. Implements the sequencing decision in
[plan-1-comparison-assembly-spec.md](../../docs/specs/plan-1-comparison-assembly-spec.md)
("Sequencing"): the rules depend on nothing preflight can reveal, so they are written first and the
declaration is what selects the reported row. Parent spec:
[penguin-deformsplat-comparison-spec.md](../../docs/specs/penguin-deformsplat-comparison-spec.md).
Companion: [phase_b_probe_verdict.md](phase_b_probe_verdict.md), whose two carve-outs §6 exists to
close._

> **Why this document exists.** Preflight will reveal whether the baseline's full-precision
> statistics record survived on the cluster, and that number feeds every reported fraction. Writing
> the rules first costs nothing and removes any question of the bar having moved once those numbers
> were visible. This project has needed that discipline once already — Phase B's T0 gate was missed
> and a noise band substituted after the fact, and it is recorded as a threshold reversal rather
> than a pass.

---

## 1. Scope of this pre-registration

Covers **Plan 1 / Deliverable 1 only**: the penguin ↔ DeformSplat comparison table, the saturation
extension of the imposed-rigidity sweep, and the wiring gate that conditions both. Deliverable 2
(region-labelled imposed rigidity) and tier 3 (geometry-derived regions) are **not** covered and
keep the preconditions the parent spec assigns them.

## 2. The replicate band — **0.0841 dB PSNR**

Every rule below that needs a noise floor uses one number, fixed here:

> **band = 0.0841 dB PSNR**

It is the full spread (max − min) of the three archived near-identical penguin runs, which are by
code inspection the same configuration:

| run | PSNR |
|---|---|
| `penguin_vanilla` (mechanism off) | 19.277395248413086 |
| `penguin_rho1a` (unit rigidity) | 19.361440658569336 |
| `penguin_rho1b` (unit rigidity) | 19.277315139770508 |

spread = 19.361440658569336 − 19.277315139770508 = **0.084125518798828**.

The band is **derived from the records by the assembler at run time, not typed into it**, so it
cannot drift from the runs it describes.

**Declared limitation.** The band was measured at unit rigidity. Every rule below applies it at high
rigidity, which assumes the replicate noise does not grow with ρ. That is an assumption, not a
measurement, and it is stated wherever the band is invoked — including in the published table.

## 3. Saturation rule — selects the reported row, mechanically

> **The reported imposed-rigidity setting is the smallest rigidity value whose PSNR falls within
> `band` of the sweep maximum.**

- **PSNR is the sole selector.** The band is measured in dB and exists only for PSNR. SSIM and
  LPIPS are reported **at the selected row**; they do not each select their own. (Confirmed by the
  user 2026-08-05 against the alternative of three independently selected rows, which the spec
  rejects as unreadable in a table.)
- **A curve that turns over is handled**: the maximum may sit mid-sweep, and the rule then returns
  the smallest rigidity within the band of that maximum, never the over-stiffened tail.
- **Ties inside the band resolve to the smallest rigidity value**, never the maximum.

### 3.1 Continuation rule

> **If the largest swept rigidity is still gaining more than `band` over its predecessor, the curve
> has not saturated: no row is reported and the sweep continues by the next declared step.**

Declared steps, in order: **ρ = 32, then 64, then 128, then 256.**

**Hard stop at ρ = 256.** If the curve has still not saturated there, that is reported as the
finding — the sweep did not saturate within the declared range — and no "swept to exhaustion" claim
is made. The sweep does not continue past 256 under any reading of the numbers.

### 3.2 Status of the rule against the sweep as it stands

Applied now to the archived imposed arm (ρ = 0.25, 1, 4, 16), the rule returns **NOT SATURATED**:
the ρ = 4 → 16 gain is **0.8489 dB**, which is 10.1 × the band. The rule therefore *demands* the
ρ = 32 and ρ = 64 runs before any row may be reported. This is recorded here to make plain that the
continuation was triggered by the criterion, not chosen after looking — the criterion was already
failing when it was written down.

## 4. Null-row treatment

> **The mechanism-off run (`penguin_vanilla`) alone constitutes the no-rigidity row** and is the
> denominator base for every reported fraction.

- **All three near-identical runs are reported together** beneath the table, with the band, so an
  examiner who notices three numbers for one configuration finds the explanation in place.
- **The equivalence between mechanism-off and unit-rigidity rests on code inspection, not on
  measurement**, and must be stated that way: `rho_scale_weights` early-returns its input at ρ = 1,
  so the two execute the same path. The gate that would have established the identity end-to-end is
  the one that failed (Phase B T0), so no measured identity is claimed.
- **Pooling the three was considered and is rejected** — it would assert an identity the record
  declines to certify. The choice is not outcome-material (pooling moves the three headline
  fractions by at most a few tenths of a percentage point), which is precisely why it is decided on
  principle here rather than on effect later.

## 5. Comparability gate

> **The assembler raises — it does not warn — unless every row agrees on all three of: the
> step-0 metric triple, the primitive count, and the evaluation step.**

- **The step-0 metric triple is the fingerprint.** A recorded checkpoint path is a string that may
  have been overwritten between runs; a matching step-0 evaluation is content-level evidence that
  the same weights were scored by the same camera on the same data. Where a source carries a
  checkpoint path it is parsed and kept as provenance, but the gate does not rest on it.
- **Mixed precision compares at the coarser precision.** The baseline is recorded at display
  precision; comparing it against a full-precision record is done at the baseline's precision.
- Failure is a hard failure. Prior experience on this project is that a silently-wrong comparison
  produces plausible numbers, which is the worst outcome available.

## 6. Wiring gate — **HARD, and its consequence is declared here**

The Phase-B verdict certifies the imposed-rigidity knob as **live** but explicitly **not** as
correctly wired: the pre-committed harness-integrity tolerance was missed by 400–1300×, and the
in-code identity assertion was a tautology (`torch.equal(weight, weight)`) that could not reach any
of the three failure modes it was the declared mitigation for.

Two independent checks close that, and both are declared before either runs:

1. **The conformance test** (local, CPU): the method repository's tested edge-weight rule and the
   cluster's rule are driven over the same graph and must agree edge-for-edge, including that
   boundary-crossing edges are untouched and that unit rigidity is a byte-exact no-op through both.
2. **The non-tautological in-run assertion** rides the saturation runs. Its rigidity value is fixed
   and independent of the run's own, so it exercises the `ρ ≠ 1` branch where the three known
   failure modes live — renormalisation, a mis-gathered neighbour index, a label-frame mismatch —
   at no additional compute.

> **Consequence, declared before the outcome is known: if either check fails, NO OUTCOME is claimed
> on the comparison.** The table is not published in any form — not scoped, not descriptive, not
> with the failure disclosed in a footnote. The finding then becomes *the seam was mis-wired*, which
> is reported as a result in its own right.

Both weaker readings were considered and are rejected here, in advance: a scoped gate preserving a
descriptive table, and publication with the failure disclosed. This project's pre-registration
apparatus exists precisely to stop a known-broken mechanism being presented as a result, and it has
been needed once already.

### 6.1 Honesty condition on a *passing* check

A passing assertion is evidence about the cluster code **as it stands now**. Preflight must confirm
the sweep sources are unchanged since the archived runs. **If they are not, the evidence does not
transfer to the archived rows**, and that limitation is recorded in the table's caption rather than
glossed. The assembler records a content hash of both rules' sources alongside the table so the
question is answerable later.

## 7. Baseline precision policy

The baseline row is the authors' unmodified pipeline, 2026-07-22 spike,
`cluster/spike_logs/phase3_run_console.log:66` — `PSNR: 25.055, SSIM: 0.9535, LPIPS: 0.056`, at
display precision (3 / 4 / 3 decimals).

> **If preflight recovers that run's full-precision `stats/val_step0501.json` from the cluster, it
> replaces the console line by a manifest edit and the table regenerates. If it does not, the
> console line stands and every fraction derived from it carries its rounding interval.**

Two constraints are declared with it:

- **Re-running the baseline to regenerate precision is prohibited.** Nondeterminism would produce a
  number disagreeing with the archived log, leaving two baseline values and an explanation owed for
  both.
- **A full-precision record only qualifies if it is the same run.** Noted before preflight because
  the trap is already visible: a local `~/results/diva360_finetune/penguin_0217_0239/stats/` exists,
  dated 2026-06-24, reading **25.0107 / 0.95367 / 0.056676**. Its step-0 fingerprint matches, but it
  does not round to the console line (25.011 ≠ 25.055), so it is a **different run** and is
  **disqualified** as the baseline row. Substituting it would be the prohibited re-run by another
  route.

The rounding interval is propagated to every affected fraction and printed beside it. On the LPIPS
column this is worth ≈ 2.2 percentage points, which is why it is stated rather than absorbed.

## 8. What is fixed by this document

| declared | value |
|---|---|
| replicate band | 0.0841 dB PSNR, derived from the three null replicates at run time |
| selector metric | PSNR; SSIM and LPIPS reported at the selected row |
| saturation rule | smallest ρ whose PSNR is within band of the sweep maximum |
| continuation steps | 32 → 64 → 128 → 256, hard stop at 256 |
| null row | `penguin_vanilla` alone; three replicates reported together |
| null equivalence | code inspection, explicitly not measurement |
| comparability gate | step-0 triple + primitive count + eval step; raises; coarser precision wins |
| wiring gate | hard; failure ⇒ no outcome claimed, mis-wiring reported as the finding |
| baseline precision | console line unless the *same run's* full-precision record is recovered |
| baseline re-run | prohibited |

## 9. Deviations

**None. 2026-08-06, execution complete: NOTHING DEVIATED.**

Every branch this document declared resolved as declared. No rule was changed, no threshold was
moved, no value in §8 was edited after the numbers arrived, and the hard gate in §6 was met rather
than merely untriggered. That is the strongest available finding about the apparatus, so it is
stated here plainly rather than buried among outcome notes.

*How* each branch resolved is a separate question, and it is recorded in §10 below rather than in
this section. The four items there are **findings, not deviations**; filing them under this heading
would invite exactly the opposite of the correct reading.

One post-hoc edit to a named artefact was made, and it is disclosed with its diff in §10.6. It
changed a sentence, not a rule.

## 10. Outcomes — how each declared branch resolved (2026-08-06)

Added after execution so this document can be audited against what happened in one pass. Nothing
above this line was edited.

### 10.1 §6.1 — do the sweep sources still match? **YES, 6/6.**

Verbatim from the preflight transcript
([`cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt`](../../cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt),
§1a), 2026-08-05T09:46:33Z on `aching`:

```
hasher: sha256sum
MATCH     util/helper.py     e83bb80d99e725b7be2831a250890f3f5b4af863d05639f0974f110588dc3220
MATCH     deform_splat.py    21ae1e32fcd45282a81552f23b3d4556d3c0499996f88ebf16bfe85ee9c2bdce
MATCH     config.py          d6facd25100c5ccce85c970eb94077f09c2eda9c0320fc0bb38bff8f7cfd5032
MATCH     util/roma.py       193f49879588108f65fcc7faea3a1a623e258c8317ab94c7a738acb35dc70667
MATCH     sweep_rho.py       95005fc2738841510388f6456c6be0e91c77438ef21d41685cc9ac4886b346d3
MATCH     measure_rho.py     edfbeb8cbae8a574a4527936eec25176ff4c724ccbf054dde1f75e417850e9bd
```

The wiring evidence therefore **transfers to the archived rows**, and no drift limitation is owed
in the table's caption. The branch where it would have been is not taken.

### 10.2 §7 — was the baseline's full-precision record recovered? **YES; the row is rebound.**

`results/diva360_finetune/penguin_0217_0239/stats/`, mtime 2026-07-22 08:34, reading
`25.054527282714844 / 0.9534690976142883 / 0.05649951100349426`. It qualifies on both declared
tests: it rounds to the console line exactly, and its step-0 triple is bit-identical to all eight
sweep rows. The manifest edit §7 specified was made and the table regenerated; the rounding
intervals collapse and the published cells are now exact.

The baseline was **not re-run** — prohibited by §7 — and the 2026-06-24 local copy §7 disqualified
in advance stayed disqualified.

*A note on what this changed downstream:* the comparability gate now holds at full precision rather
than at three decimals, and the published LPIPS cell moved from 79.2% to 80.4% because the **input**
sharpened. A separate claim that Plan 1 *corrected* the parent spec's SSIM cell has been
**retracted** — the console-baseline interval had contained that cell all along. The retraction is
in [`docs/specs/plan-1-comparison-assembly-spec.md`](../../docs/specs/plan-1-comparison-assembly-spec.md);
it is not a deviation, because the claim was never part of this document.

### 10.3 §6 — did the in-run wiring assertion fire? **NO, on either run.**

Neither `penguin_rho32.log` nor `penguin_rho64.log` carries an `AssertionError` or a traceback;
both reached step 501 and wrote statistics. Both logs record the patched source's hash inline, so
the runs self-identify against the version now archived at
[`cluster/sources_20260805_patched/`](../../cluster/sources_20260805_patched).

The local half of the gate — the conformance test — passes as well. **The hard gate in §6 is met,
so an outcome may be claimed.**

Silence is only evidence if the check could have spoken, and this project has retracted one
assertion that could not. The block is now driven against deliberately broken rules by
`tests/test_wiring_assertion.py` in the comparison repository: it stays silent on the correct rule
and fires on renormalisation, a mis-gathered neighbour index, a wrong rigid-region id, a mis-scaled
rigid interior and an empty rigid interior. It **cannot** fire on a label-frame mismatch, for the
reason given in the verdict; that is a property of the block, and the acceptance criterion demanding
such a demonstration is amended on its ticket rather than dropped.

### 10.4 §3.1 — did the sweep saturate? **YES, at the second continuation step; ρ = 16 selected.**

The two declared runs were executed (2026-08-05, ~9.5 min each). The curve turned over:

| ρ | PSNR |
|---|---|
| 16 | 22.9534 |
| 32 | 21.8276 |
| 64 | 20.7387 |

The rule was applied by **running the selector**, not by eye: last gain −1.0889 dB ≤ the 0.0841 dB
band, so it returns SATURATED, and the smallest rigidity within the band of the maximum is ρ = 16.
The continuation ladder stopped at 64 without reaching the hard stop at 256. The published table
reads **63.6% / 72.6% / 80.4%**.

### 10.5 §4, §5, §2 — unchanged and applied as declared

The null row is `penguin_vanilla` alone, its equivalence still labelled code inspection rather than
measurement; the comparability gate raised on nothing, with all nine rows agreeing on the step-0
triple, the primitive count and the evaluation step; the replicate band was derived at run time from
the three null replicates, not typed in, and came out at 0.0841 dB.

### 10.6 The one post-hoc edit to a named artefact, disclosed

`plan1/saturation.py`'s **reason sentence** was edited after the numbers were seen. §8 fixes the
*rule*; it does not fix the sentence describing it. The old wording rendered a turned-over curve as
`"rho=64 gains -1.0889 dB over its predecessor, within the 0.0841 dB band"` — a negative quantity
called a gain, and a 1.09 dB fall called "within" a 0.08 dB band — in the sentence that names the
reported setting.

```diff
-            f"saturated: rho={largest.rigidity:g} gains {last_gain:.4f} dB over its "
-            f"predecessor, within the {band:.4f} dB band. Smallest rigidity within "
-            f"the band of the maximum ({maximum.psnr:.4f} dB at "
-            f"rho={maximum.rigidity:g}) is rho={selected.rigidity:g}"
+            f"saturated: {_movement(largest, last_gain, band)}. Smallest rigidity "
+            f"within the band of the maximum ({maximum.psnr:.4f} dB at "
+            f"rho={maximum.rigidity:g}) is rho={selected.rigidity:g}"

+def _movement(largest, last_gain, band):
+    if last_gain < 0.0:
+        return (f"the curve has turned over — rho={largest.rigidity:g} falls "
+                f"{-last_gain:.4f} dB below its predecessor")
+    return (f"rho={largest.rigidity:g} gains {last_gain:.4f} dB over its predecessor, "
+            f"within the {band:.4f} dB band")
```

The predicate `saturated = last_gain is not None and last_gain <= band` is untouched, and the
decision is pinned by test **before and after** the edit
(`test_the_wording_change_cannot_move_which_row_is_reported`): saturated, ρ = 16 selected, maximum
at ρ = 16, ladder exhausted. A prose edit provably could not move which row is reported.
