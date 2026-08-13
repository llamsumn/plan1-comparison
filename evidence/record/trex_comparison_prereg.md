# Trex — PRE-REGISTRATION for the comparison table (rules declared before the table is assembled)

_Authored 2026-08-12, **before** the native baseline arm ([#41](https://github.com/llamsumn/3D-arap/issues/41))
is run, before the saturation runs ([#42](https://github.com/llamsumn/3D-arap/issues/42)) are launched,
and before this author read any trex ρ-sweep PSNR value. Delivers
[#40](https://github.com/llamsumn/3D-arap/issues/40). Model, and the source of every rule this
document does not restate: [plan1_prereg.md](plan1_prereg.md) — the penguin's. Per [no-git-commands]
the user commits; written to the working tree only._

> **Why this document exists.** The penguin table's standing rests on the rule having been fixed in
> advance, and the comparison repository carries a test asserting that the rule, applied to the sweep
> as it then stood, said *continue* — i.e. it is on record disagreeing with what was already there. A
> trex row assembled under a rule written after the trex numbers were seen would sit beside the
> penguin row with visibly weaker standing, and that asymmetry is exactly what a reader looks for.

> **Drafting condition, stated because it is the whole value of the document.** No trex ρ-sweep PSNR,
> SSIM or LPIPS value was read, printed or glanced at while this was written. The step-0 triple *was*
> used — it is already public in the bodies of #40 and #41, it is a fingerprint rather than a result,
> and §4 turns on it.

---

## 1. Scope

Covers the **trex ↔ DeformSplat comparison table** and nothing else: its own manifest, its own table,
the baseline gate (#41), the saturation extension (#42) and publication (#43).

**Explicitly not covered:**

- The roughness-slope diagnostic on trex (#46). That was governed by its own, now-spent
  pre-registration, [`../item2_mask/trex_roughness_prereg.md`](../item2_mask/trex_roughness_prereg.md),
  and its result stands independently of everything here.
- Deliverable 2 (region-labelled imposed rigidity) and tier 3 (geometry-derived regions), which keep
  the preconditions the parent spec assigns them.

> **A confusion this document exists partly to prevent.** If this chain completes it delivers
> `n = 2` **on the comparison table**. That is a different result from #46's roughness finding, where
> Boundary 1 already moved to `n = 2` **for the roughness slope only**. Neither carries the other, and
> the accepted headline — *medial-thickness estimation fails on this reconstruction, and roughness at
> every resolvable scale is the mechanism* — is not what this table is about.

## 2. What is inherited, and therefore not re-derived here

These rules are already fixed, already written down and already machine-implemented in
`~/plan1-comparison`. This document **binds to them**; it does not restate them, and a restatement
would only create a second copy that can drift.

| rule | where it is declared | where it is implemented |
|---|---|---|
| Saturation rule and the continuation ladder | [plan1_prereg.md](plan1_prereg.md) §3, §3.1 | `plan1/saturation.py`, pinned by `tests/test_saturation.py` |
| Null-row treatment, and the code-inspection basis of null ≡ unit rigidity | §4 | manifest roles `null` / `null_replicate` |
| Comparability gate — step-0 triple + primitive count + eval step, **raises**, coarser precision wins | §5 | the assembler |
| Baseline precision policy, and the prohibition on re-running a baseline | §7 | manifest row binding |
| Wiring gate | §6, discharged 2026-08-06 (§10.3), sources 6/6 MATCH (§10.1) | `tests/test_wiring_assertion.py`, `tests/test_conformance.py` |

**Precedence, declared now so it never has to be argued later:** where this document and
`plan1_prereg.md` appear to differ, **`plan1_prereg.md` governs the rule and this document governs
only the trex-specific bindings** — the band, the manifest, the gate values, the branches, the
prediction. This document may not weaken an inherited rule.

### 2.1 The one inherited item that does **not** transfer for free — the wiring evidence

The wiring gate was discharged against sources hashed on the node **2026-08-05**. The trex ρ-sweep
was run **2026-07-26**. The discharge is evidence about the code that produced the runs it was
checked against, and transferring it to trex is an inference, not a measurement.

> **Declared: the trex rows inherit the wiring discharge only if the sources that produced them hash
> to the six values recorded in [plan1_prereg.md](plan1_prereg.md) §10.1.** #41 and #42 must record
> their source hashes inline in the console log, as the penguin saturation runs did. If a hash for
> the pre-existing six trex rows cannot be established, **the limitation goes in the table's caption**
> under the honesty condition of §6.1 rather than being glossed — it does not block publication, and
> it is not silently assumed away either.

## 3. The replicate band — derived from **trex's own** replicates, and deliberately absent from this document

> **band_trex = max − min of the step-501 PSNR of `trex_vanilla`, `trex_rho1a`, `trex_rho1b`**,
> derived by the assembler **at run time from the records, never typed in**.

Three near-identical trex runs exist and are the exact structural analogue of the penguin's three:

| run | role | record |
|---|---|---|
| [`trex_vanilla`](../../cluster/rho_probe_evidence/trex_vanilla) | mechanism off | `stats/val_step0501.json` |
| [`trex_rho1a`](../../cluster/rho_probe_evidence/trex_rho1a) | unit rigidity, replicate a | `stats/val_step0501.json` |
| [`trex_rho1b`](../../cluster/rho_probe_evidence/trex_rho1b) | unit rigidity, replicate b | `stats/val_step0501.json` |

**Its value is not written in this document, and that is deliberate.** The penguin's §2 fixes the band
by *rule* precisely so that it "cannot drift from the runs it describes"; typing trex's number here
would require reading it, which this document is written not to do.

**The penguin's 0.0841 dB does not govern trex, and may not be substituted.** A band measured on a
different asset selecting trex's reported row is exactly the drift the derive-at-run-time rule exists
to prevent.

**If the derivation cannot run** — a replicate record missing, unreadable, or failing the
comparability gate — **there is no band, and therefore no row.** No fallback band, no penguin
substitute, no widening.

**Declared limitation, carried across from the penguin unchanged.** The band is measured at unit
rigidity and applied at high rigidity, which assumes replicate noise does not grow with ρ. That is an
assumption, not a measurement, and it is stated wherever the band is invoked — **including in the
published table**.

## 4. The baseline gate (#41) — stated numerically, and its premise is now settled

> **A fresh native DeformSplat run on trex qualifies as the baseline row only if its step-0 record
> matches the six existing sweep rows exactly:**
>
> | field | required value |
> |---|---|
> | PSNR | `18.714893341064453` |
> | SSIM | `0.8961969614028931` |
> | LPIPS | `0.10315407812595367` |
> | `num_GS` | **17,779** |
> | evaluation step | 501 (`stats/val_step0501.json`); step-0 record `stats/val_step0000.json` |

**Comparison is at full precision.** The inherited coarser-precision rule (§5) exists for a baseline
recorded only at display precision; trex's six sweep rows carry full-precision statistics records and
#41's run will too, so the gate is exact equality, not agreement to three decimals. **The gate may not
be relaxed to display precision to rescue a near-miss.**

### 4.1 The 17,779 vs 33.6k question is **resolved**, not open

#40's ticket body calls the difference "unexplained". **It was explained on 2026-08-11** and this
document supersedes that wording rather than carrying it into a sealed record:

- `ckpt_best_psnr.pt` was written at **step 2999** with `num_GS` **17,779**; training ran on to step
  9999, where `ckpt_9999_rank0.pt` carries **33,623**. One run, two moments — two correct numbers
  describing two different files. Confirmed against the fetched files directly (`step` field and
  `means` shape), not inferred from the log or from file sizes.
- All three surviving rho-probe containers ran `--ckpt results/diva360/trex_0135/ckpts/ckpt_best_psnr.pt`
  verbatim, so **the entire trex ρ-probe ran on the 17,779-primitive model.**

Source: [trex_checkpoint_provenance.md](trex_checkpoint_provenance.md). **The gate above therefore
stands unchanged and needs no amendment**, and the most likely cause of a step-0 mismatch has been
ruled out before any GPU time is spent.

### 4.2 The NO-GO branch, declared before the number is seen

> **If the triple does not match, no trex row is published by this route.** The two runs did not begin
> from the same state, the comparability gate would refuse the table, and that is the answer.

Declared with it, so none of these can be reached for afterwards:

- **Do not retrain trex** to manufacture a matching state. It would be the prohibited baseline re-run
  by another route (§7's reasoning, applied to the other arm).
- **Do not substitute `ckpt_9999_rank0.pt`** (33,623). It is a different model and nothing else in the
  chain consumes it.
- **Do not relax the gate**, widen it to a tolerance, or publish a scoped/descriptive table with the
  mismatch disclosed in a footnote.
- #42 and #43 close as **blocked**, and the NO-GO is recorded as a finding with the numbers behind it.

## 5. The saturation rule as applied to trex — every branch declared

The rule itself is inherited (§2). What is fixed here is **what is fed to it** and **what happens on
each outcome**.

**Fed to the rule: the imposed arm only** — ρ = 0.25, 4, 16, plus any continuation runs. Declared
explicitly because the exclusions matter:

- The **unit-rigidity replicates are not fed.** They would duplicate ρ = 1 in the sweep, and choosing
  between them is precisely the arbitrary decision the manifest exists to prevent.
- The **mechanism-off run is not a sweep point.** It is the null row and the denominator base.

> **A discrepancy in the inherited record, resolved here rather than inherited silently.**
> [plan1_prereg.md](plan1_prereg.md) §3.2 describes the rule being applied to *"ρ = 0.25, 1, 4, 16"*,
> counting unit rigidity as a sweep point in prose; the penguin **manifest**, which is what actually
> ran, excludes both replicates for the reason above. **Trex follows the manifest** — the behaviour
> that produced the published penguin row — and the divergence is recorded so a reader comparing the
> two documents does not read it as trex quietly changing the input set.

**Applied by running the selector, never by eye.** The verdict must come from
`select_saturated_row(...)`, and its `reason` string is recorded verbatim in §12.

### 5.1 The three branches

| branch | outcome | consequence |
|---|---|---|
| **A — SATURATED on the rows that already exist** (ρ = 0.25, 4, 16) | the rule returns a selected ρ | that row is reported. **#42 is then unnecessary and is not run.** Declared in advance so that an appetite for the extra runs cannot override the rule |
| **B — NOT SATURATED** | the largest swept ρ is still gaining more than the band | continue by the inherited ladder: **ρ = 32, then 64, then 128, then 256**. #42 covers 32 and 64 |
| **C — ladder exhausted at ρ = 256 without saturating** | hard stop | the finding is *the sweep did not saturate within the declared range*. **No row is published**, and no "swept to exhaustion" claim is made |

### 5.2 NOT SATURATED is a declared success branch

> **If the rule returns NOT SATURATED at the end of the declared ladder, no row is published and that
> is the pre-committed outcome — a result, not a failure to work around.**

Specifically forbidden as responses to it: extending the ladder past 256; widening the band; switching
the selector from PSNR to SSIM or LPIPS; reporting the argmax instead; publishing a descriptive or
scoped table in place of the real one. Each of these would convert a declared branch into a defeat to
be engineered around, which is the failure mode this apparatus exists to stop and which this project
has needed it for once already.

### 5.3 One deliberate difference from the penguin's §3.2, disclosed rather than left to be noticed

The penguin's pre-registration recorded the rule's verdict **against the sweep as it stood at write
time**, which put it on record disagreeing with what was already there — a strong demonstration, and
it required reading those numbers.

**This document does not do that**, because it was drafted without reading trex's ρ-sweep results at
all. That is stronger on blindness and forgoes the demonstration. Both halves are stated because a
reader comparing the two documents will notice the missing section.

**Pre-committed in its place:** the *first* application of the rule to trex is recorded in §12 with its
`reason` string verbatim, whatever it returns — including branch A, which would make #42 moot and
would otherwise be the most tempting outcome to re-open the rule over.

### 5.4 What is prospective here, and what is not — stated plainly

Six trex rows already existed when this was written: they were produced by the **C-pilot on
2026-07-26**, and their metrics have been in this repository ever since, including in
[phase_c_plan.md](phase_c_plan.md). This document therefore **cannot** claim the trex sweep is unseen
by the project — only that its author did not consult it.

What is genuinely prospective: **the rule's application, the selected row, the baseline arm (#41) and
the continuation runs (#42).** That is the same structure the penguin had — four of its rows also
pre-existed its pre-registration and two were prospective — so the trex table is not weaker on this
axis than the row it will sit beside. Stated rather than assumed.

## 6. Manifest shape, row bindings, and the separate-table decision

> **Trex gets its own manifest and its own table. Its rows are never added to the penguin's.**

The comparability gate keys on the step-0 triple, the primitive count and the evaluation step. Mixing
assets would make it **raise**, correctly. The penguin's `out/comparison_table.md` stays
byte-identical, and its manifest is not touched.

- manifest: `manifests/trex_deformsplat.toml`
- table: `out/trex_comparison_table.md`

**Header constants:**

| key | value |
|---|---|
| `asset` | `"trex_0135_0250"` — frames 0135 → 0250 ([phase_c_plan.md](phase_c_plan.md), object-selection table). Transcribed from #41's run record at manifest-authoring time, not assumed |
| `eval_step` | `501` |
| `assembled` | the assembly date, **declared, not stamped at render time** — `date.today()` once made the committed table a different file every day, so the claim that it regenerates was true only on the day it was published. Adding or rebinding a row means changing this line too |
| `[roots] archive` | `"../evidence"` — evidence **vendored** into the comparison repository with a `PROVENANCE.toml` entry and hashes. A published number may not depend on a sibling checkout an examiner does not have |

**Rows, bound explicitly:**

| `key` | `role` | `rigidity` | `path` (under `archive`) | status |
|---|---|---|---|---|
| `vanilla` | `null` | — | `cluster/rho_probe_evidence/trex_vanilla` | exists |
| `rho1a` | `null_replicate` | 1.0 | `.../trex_rho1a` | exists |
| `rho1b` | `null_replicate` | 1.0 | `.../trex_rho1b` | exists |
| `rho025` | `imposed` | 0.25 | `.../trex_rho025` | exists |
| `rho4` | `imposed` | 4.0 | `.../trex_rho4` | exists |
| `rho16` | `imposed` | 16.0 | `.../trex_rho16` | exists |
| `rho32` | `imposed` | 32.0 | `.../trex_rho32` | **#42, branch B only** |
| `rho64` | `imposed` | 64.0 | `.../trex_rho64` | **#42, branch B only** |
| `baseline` | `baseline` | — | `.../baseline_trex_0135_0250` | **#41** |

All rows are `kind = "stats_json"`, `root = "archive"`.

**`information` is a column, not a footnote** — it is the frame of the comparison. It describes what
each *arm* was given, so it transfers from the penguin unchanged: `"static asset + one handle"` for
every ours-arm row, `"observed before/after motion"` for the baseline. The baseline has seen the
object move; the column carries that fact wherever the table travels.

**Binding discipline, inherited and restated because it is a trex-specific hazard too:** rows are bound
to sources **explicitly**, never inferred from directory names and never from the numbers themselves.
On the penguin, `vanilla` and `rho1b` differ by less than 0.0001 dB and are separable only on the
secondary metrics; any heuristic binding would eventually swap them and produce a table that is wrong
in a way that looks entirely plausible. **Whether trex's replicates are that close is not known to
this document and is not assumed either way** — the binding is explicit regardless. Adding a run is an
edit to the manifest. No number is ever retyped into a chapter.

## 7. Where this document lives, and what happens to it if #43 is cut

**Authored in `~/3D`** (the workbench), **ported to `~/plan1-comparison/evidence/record/` on
publication** — which is #43's job, and is exactly how `plan1_prereg.md` came to exist in both
repositories. Under [two-repo-discipline] only workable results port across.

**#43 is the designated cut** ([plan_decisions_2026-08-11.md](plan_decisions_2026-08-11.md) D6) — the
first thing dropped if the calendar tightens. Recorded here so the position cannot be misread later:

- The reservation extension to **2026-11-25** relieves **#41 and #42**, which are GPU-bound. It does
  **not** relieve #43, which needs no cluster at all and whose real constraint was always the
  **2026-09-07** write-up calendar. #43's inherited 08-26 hard stop was withdrawn on the ticket as the
  wrong constraint. **The cut designation is not made obsolete by the extension.**
- **If #43 is cut, this document stays in the workbench and no trex row is published.** That is a
  coherent end state, not a loose end: the published evidence stays at one asset, the `n = 1`
  objection stays open on the comparison, and `main` plus `submission-green-20260810` remains a
  complete submittable artefact. A half-integrated second asset is strictly worse than none.

## 8. What is predicted — the bar-vs-blob prediction, stated in advance

Stating this before the table exists is what makes a confirmed second asset stronger than an extra
data point.

**The geometry, measured 2026-07-29:** trex is the **elongated bar-analog**, PCA aspect **4.27**,
against the penguin's **compact blob-analog** at **2.53**. **The C-pilot (2026-07-26) found trex's
near/far concentration ratio swinging 0.61 → 1.68 — crossing 1** — where on the penguin ρ *tightens* an
already-concentrated field (near/far 3.0 → 4.15) without crossing anything. On trex, ρ converts a
default-global deformation into a locally concentrated one; on the penguin it concentrates what was
already concentrated. Sources: [phase_c_plan.md](phase_c_plan.md), [verdict.md](verdict.md).

> **P1 — primary, and given a number so it can fail.** Imposed rigidity closes a **substantial**
> fraction of the null → baseline gap on trex, in the same direction as the penguin.
>
> | PSNR gap closed | verdict, pre-committed |
> |---|---|
> | **> 50%** | the penguin result **reproduces** on a second, differently-shaped asset |
> | **25 – 50%** | **equivocal**, and published as equivocal — not as a reproduction |
> | **< 25%** | **fails to reproduce**; see §9.4 |
>
> The penguin's figure is 63.6% PSNR. The thresholds are set relative to it and are fixed here.

> **P2 — the selected ρ is deliberately NOT predicted.** The penguin's curve turned over between
> ρ = 16 and ρ = 32. Because ρ changes the *character* of trex's deformation rather than only its
> magnitude, there is no ground to expect the same turnover point, and predicting one would be
> decoration. Whatever the rule selects is the answer.

> **P3 — the three fractions are expected to *differ* from 63.6 / 72.6 / 80.4.** A second asset
> reproducing the penguin's percentages closely would be surprising rather than reassuring, and would
> itself warrant a look at whether the two tables are truly independent.

**A caveat carried forward from the pilot, so it is not over-read:** trex is elongated *relative to the
penguin*. It was never a synthetic bar, and nothing here claims the pure-ARAP bar/blob split has been
reproduced on a canonical bar.

## 9. Falsification clause — what would make this pre-registration wrong

Written so it can be checked later, in the style the penguin's own used, where exactly this clause is
the one that fired.

1. **The baseline gate fires (§4).** #41's step-0 triple does not match. Then the premise that a native
   baseline can be produced from the same state on this asset is **wrong**, and no trex row exists by
   this route.
2. **Branch C (§5.1).** The curve does not saturate by ρ = 256. Then the inherited ladder is wrong for
   this asset — it was calibrated on the penguin — and the pre-registration's choice of range is what
   failed.
3. **The band assumption (§3).** If the replicate spread at high ρ is ever measured and materially
   exceeds the unit-rigidity band, every selection made with that band is retrospectively suspect.
   This is not measured and is declared as an assumption, not established.
4. **P1 fails (< 25%).** Then geometry-dependence at the render loop does **not** transfer the way the
   C-pilot's near/far crossing suggested. That is a finding and is published as one — and the penguin
   result is then stated explicitly as `n = 1` on the comparison, not quietly left implying more.
5. **The wiring evidence does not transfer (§2.1).** The trex sweep's sources hash differently from
   §10.1's six. Then the caption carries the limitation, and the wiring discharge is the penguin's
   alone.

> **Named in advance: the clause most likely to fire is #1, the baseline gate.** It is the only one
> that turns on a fresh run reproducing an archived state exactly, it is why #41 is a separate ticket,
> and it is why #41 costs one run rather than three.

## 10. What is fixed by this document

| declared | value |
|---|---|
| replicate band | trex's own, derived at run time from `trex_vanilla` / `trex_rho1a` / `trex_rho1b`; **never typed**; penguin's 0.0841 dB does not apply |
| band limitation | measured at unit rigidity, applied at high ρ; stated wherever invoked, including in the published table |
| selector metric | PSNR (inherited); SSIM and LPIPS reported at the selected row |
| saturation rule | inherited from `plan1_prereg.md` §3 / `plan1/saturation.py`; applied by running it |
| fed to the rule | imposed rows only — ρ = 0.25, 4, 16 + continuations; replicates and vanilla excluded |
| continuation ladder | 32 → 64 → 128 → 256, hard stop at 256 (inherited) |
| baseline gate | exact match on `18.714893341064453` / `0.8961969614028931` / `0.10315407812595367` / `num_GS` 17,779 at step 0, full precision |
| NO-GO consequence | no row by this route; no retrain, no 33,623 substitute, no relaxed gate; #42 and #43 blocked |
| NOT SATURATED | declared success branch; no row, no ladder extension, no band widening, no selector switch |
| table shape | separate manifest `trex_deformsplat.toml`, separate table `out/trex_comparison_table.md`; penguin's stays byte-identical |
| row bindings | explicit, never inferred from directory names or from the numbers |
| wiring evidence | transfers only on a source-hash match to §10.1; otherwise the caption carries the limitation |
| authored / ported | authored in `~/3D`; ported to `~/plan1-comparison/evidence/record/` on publication (#43) only |
| prediction | P1 with pre-committed thresholds (>50% / 25–50% / <25% on PSNR); selected ρ not predicted |

## 11. Deviations

_Filled 2026-08-12 on publication (#43), in one pass with §12. **Nothing above this line was edited.**
Two of the sealed sections can be checked rather than taken on trust: `~/plan1-comparison` pinned §4's
four gate values as `GATE_START` / `GATE_PRIMITIVES` and §5.3's `reason` string as
`FIRST_VERDICT_REASON` in `tests/test_trex_assembly.py`, committed **before** any table was rendered
and before any fraction was read. A later edit to §4 or §5.3 would put this document out of agreement
with a test that predates it._

**Two, and neither changes a rule.**

### 11.1 §9's clause 5 was written as a binary, and the answer was neither of its two branches

Clause 5 declared: *"The wiring evidence does not transfer (§2.1). The trex sweep's sources hash
differently from §10.1's six."* It anticipated **match** or **differ**. What was found is a third
state the clause did not have a name for.

The archived source snapshot hashes **6/6 identically** to §10.1 — helper.py, deform_splat.py,
config.py, roma.py, sweep_rho.py and measure_rho.py, hashed directly rather than transcribed. So the
clause's stated trigger did not fire. But the snapshot was taken **2026-07-29** and the sweep ran
**2026-07-26**, and the trex consoles carry no inline source hashes, because echoing them inline only
began with the 2026-08-05 saturation runs. The match therefore **brackets** these runs rather than
pinning them: unchanged from 2026-07-29 through the 2026-08-05 preflight is measured; unchanged from
2026-07-26 to 2026-07-29 is not.

**The consequence clause 5 prescribed was applied anyway** — the caption carries the limitation, per
§2.1 and §6.1's honesty condition. Recorded here because the defect is in the *clause*, not in the
execution: a falsification clause that offers two branches when the evidence can land in three is a
clause that would have let a partial answer be reported as a clean one. The penguin's own six sweep
rows sit in exactly this position (run 2026-07-25, same snapshot, same three-day gap) and §10.1
accepted the transfer on that basis, so trex is no weaker on this axis than the row it sits beside —
which is the reason this is a stated limitation rather than a blocking finding.

### 11.2 The manifest carries two declared keys beyond §6's header-constants table

§6 enumerated `asset`, `eval_step`, `assembled` and `[roots] archive`. `manifests/trex_deformsplat.toml`
also declares:

| key | what it is | why it is a binding and not a rule |
|---|---|---|
| `prereg` | the pre-registration the table's byline cites — **this document**, not the penguin's | the byline was a constant in the renderer while there was one table. With two, a fixed byline would send a reader of the trex table to a file that declares neither its band nor its gate values. Which document governs a table is a fact about that table |
| `limitations` | the §2.1 wiring limitation, as the text rendered into the table's own Limitations list | this is **how §2.1 was discharged**, not a departure from it. §2.1 required the limitation to reach the table's caption; a limitation left in a manifest comment reaches nobody, and one left in prose beside the table is one edit from vanishing in the flattering direction |

Neither weakens an inherited rule, so both sit inside §2's precedence clause. Recorded because §6
enumerated the header constants and an enumeration that has quietly grown is worth as little as a
count that has.

## 12. Outcomes — how each declared branch resolved

_Filled 2026-08-12 on publication (#43), in one pass, from the assembled table rather than from any
plan document. The table is `~/plan1-comparison/out/trex_comparison_table.md`; it regenerates
byte-identically from `manifests/trex_deformsplat.toml` and the vendored evidence, and the green gate
diffs it._

### 12.1 The baseline gate (§4) — **GO**, and the clause named most likely to fire did not

All four fields matched at **full precision**, not to display precision:

| field | §4 requires | #41 recorded |
|---|---|---|
| PSNR | `18.714893341064453` | `18.714893341064453` |
| SSIM | `0.8961969614028931` | `0.8961969614028931` |
| LPIPS | `0.10315407812595367` | `0.10315407812595367` |
| `num_GS` | 17,779 | 17,779 |

Source: the run's own `stats/val_step0000.json`, read directly rather than off the console line — the
console printed three decimals, and §4 forbids relaxing to display precision to rescue a near-miss.
Full record: [trex_baseline_gate.md](trex_baseline_gate.md).

**§9 clause 1 was named in advance as the one most likely to fire. It did not fire.** §4.2's NO-GO
branch was therefore never reached, and none of the things it forbade — retraining, substituting the
33,623-primitive checkpoint, relaxing the gate — was needed or done.

### 12.2 The saturation rule (§5) — **branch A**, and the first application's reason string verbatim

> `saturated: the curve has turned over — rho=16 falls 1.5833 dB below its predecessor. Smallest rigidity within the band of the maximum (24.1106 dB at rho=4) is rho=4`

Returned by `select_saturated_row(...)` through the assembler, fed the imposed arm only — ρ = 0.25, 4,
16 — exactly as §5 declared. This is the **first** application of the rule to trex, recorded whatever
it returned, per §5.3. It was pinned in `tests/test_trex_assembly.py::FIRST_VERDICT_REASON` before any
table existed.

**Branch A: the reported row is ρ = 4, and #42 is therefore unnecessary and was not run.** §5.1
declared that consequence in advance precisely because it is the outcome an appetite for the extra
runs would want to override. #42 closed **unrun**, which is pre-registered rather than a judgement
call.

The curve **turned over** rather than flattening — ρ = 16 falls 1.5833 dB *below* ρ = 4, and only one
point qualifies within the band at all — so being the largest swept value bought ρ = 16 nothing.
Branch C was never in play: the ladder was not entered, and the hard stop at ρ = 256 was not reached.

### 12.3 The replicate band (§3) — derived, never typed

**0.019285202026367188 dB**, derived by the assembler at run time from trex's own three null-family
rows (`trex_vanilla`, `trex_rho1a`, `trex_rho1b`). It appears in no manifest, in no chapter, and in
this document only here, in the record of what happened rather than as an input to it.

**The penguin's 0.0841 dB governed nothing.** A test asserts the two differ, and another asserts the
trex manifest carries no key with a band in it — checked over the parsed keys rather than the prose,
so that the manifest stays free to *explain* the rule in a comment.

§3's declared limitation stands and travels: the band was measured at unit rigidity and applied at
high rigidity, which assumes replicate noise does not grow with ρ. That is an assumption, not a
measurement, and it is printed in the published table's Limitations list.

### 12.4 P1 (§8) — **> 50%. The penguin result reproduces on a second, differently-shaped asset**

| metric | none (ρ off) | imposed, ρ = 4 | baseline | gap closed |
|---|---|---|---|---|
| PSNR | 22.615 | 24.111 | 24.777 | **69.2%** |
| SSIM | 0.9305 | 0.9390 | 0.9428 | **69.0%** |
| LPIPS | 0.0662 | 0.0571 | 0.0541 | **74.9%** |

§8 pre-committed the bands on the PSNR gap closed before any trex fraction was read: **> 50%**
reproduces, **25–50%** equivocal and published as equivocal, **< 25%** fails. **69.2% is the first
branch.** §9 clause 4 did not fire.

Every cell is **exact** — no rounding interval anywhere in the table. Trex's baseline arm was run
natively into its own full-precision statistics record, which is what #41 bought; the penguin's
baseline began as a three-decimal console line and its fractions carried brackets until preflight
recovered the full-precision record.

**What this does and does not license.** It is `n = 2` **on the comparison table**, and nothing more.
It is not #46's `n = 2`, which moved Boundary 1 for the **roughness slope only**; neither result
carries the other, and the accepted headline is unchanged — medial-thickness estimation fails on this
reconstruction, and roughness at every resolvable scale is the mechanism. The §8 caveat also stands:
trex is elongated *relative to the penguin* (PCA aspect 4.27 against 2.53). It was never a synthetic
bar, and no claim is made that the pure-ARAP bar/blob split has been reproduced on a canonical one.

### 12.5 P2 (§8) — not predicted, and the two assets did not agree

The rule selected **ρ = 4**. The penguin's rule selected ρ = 16. §8 declined to predict a turnover
point on the ground that ρ changes the *character* of trex's deformation rather than only its
magnitude, and predicting one would have been decoration. Recorded because "not predicted" is only
worth stating while it is also true that the two came out different.

### 12.6 P3 (§8) — the three fractions differ, as predicted

69.2 / 69.0 / 74.9 against the penguin's 63.6 / 72.6 / 80.4. §8 stated in advance that a close match
would be **surprising rather than reassuring**, and would warrant asking whether the two tables were
genuinely independent. They differ, and they differ in pattern as well as in value: the penguin's
three ascend PSNR → SSIM → LPIPS, where trex's first two sit within 0.2 points of each other. No
question about independence arises.

### 12.7 The wiring evidence (§2.1) — partial, and the caption carries it

6/6 hash match on a snapshot that **brackets** the sweep rather than pinning it. See §11.1 for why
this is neither of §9 clause 5's two branches, and the published table's Limitations list for the text
a reader actually meets. The baseline row is the exception and is stronger: its console echoes all six
hashes inline, five matching §10.1 and `deform_splat.py` reading the patched call site that could not
have touched it — the patch is wholly inside `if getattr(self.cfg, 'rho_enabled', False):`, only the
sweep wrapper sets that flag, and step 0 is evaluated upstream of the block regardless.

### 12.8 The table's shape (§6) and this document's home (§7)

- **Separate manifest, separate table, as declared.** `manifests/trex_deformsplat.toml` →
  `out/trex_comparison_table.md`. Trex rows were never added to the penguin's manifest, and a test
  asserts the two are assembled from disjoint evidence.
- **The penguin's table stays byte-identical.** Its manifest gained the `prereg` key (§11.2) declaring
  the byline it already printed, so the rendered bytes are unchanged, and the green gate rebuilds and
  diffs both tables on every run.
- **§7 executed rather than cut.** #43 was the designated cut and was not taken; this document is
  ported to `~/plan1-comparison/evidence/record/` with §11 and §12 filled, byte-exact and pinned by
  sha256 in `evidence/PROVENANCE.toml`, per §7 and [two-repo-discipline].
- **§5.4's honesty about what was prospective stands unchanged.** Six trex rows pre-existed this
  document and their metrics had been in the workbench since 2026-07-26. What was genuinely
  prospective — the rule's application, the selected row, and the baseline arm — is what §12.1 and
  §12.2 record.
