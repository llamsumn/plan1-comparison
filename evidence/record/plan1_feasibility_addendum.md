# Plan 1 — feasibility addendum (preflight, 2026-08-05)

_The dated addendum [plan1_cluster_handoff.md](plan1_cluster_handoff.md) said would return here.
It records what preflight found, and specifically the observations that **changed how the
remaining work executes**. The transcript it summarises is archived verbatim at
[`cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt`](../../cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt);
nothing below is a substitute for reading it._

Run 2026-08-05T09:46:33Z on `aching` as `clll20`, root `/homes/clll20/deformsplat`.
Observation only — preflight ran nothing that could change a published number.

---

## 1. The load-bearing result: sources unchanged, so the evidence transfers

[plan1_prereg.md](plan1_prereg.md) §6.1 makes a passing wiring check evidence about the cluster
code **as it stands now**, and requires that preflight confirm the sweep sources are unchanged
since the archived runs — *if they are not, the evidence does not transfer to the archived rows*,
and that limitation goes in the table's caption rather than being glossed.

It confirmed them. Verbatim from §1a of the transcript:

```
hasher: sha256sum
MATCH     util/helper.py     e83bb80d99e725b7be2831a250890f3f5b4af863d05639f0974f110588dc3220
MATCH     deform_splat.py    21ae1e32fcd45282a81552f23b3d4556d3c0499996f88ebf16bfe85ee9c2bdce
MATCH     config.py          d6facd25100c5ccce85c970eb94077f09c2eda9c0320fc0bb38bff8f7cfd5032
MATCH     util/roma.py       193f49879588108f65fcc7faea3a1a623e258c8317ab94c7a738acb35dc70667
MATCH     sweep_rho.py       95005fc2738841510388f6456c6be0e91c77438ef21d41685cc9ac4886b346d3
MATCH     measure_rho.py     edfbeb8cbae8a574a4527936eec25176ff4c724ccbf054dde1f75e417850e9bd
```

**6/6 MATCH.** No drift limitation is owed on the archived rows. This is why the wiring evidence
is stated without a caption qualifier in the verdict.

The single later divergence is deliberate and accounted for: `deform_splat.py` was then patched to
carry the non-tautological assertion, becoming `e2ca10cf…`, which is the version the ρ = 32 and
ρ = 64 runs went through. It is archived byte-exact at
[`cluster/sources_20260805_patched/`](../../cluster/sources_20260805_patched) with the one-hunk
diff recorded beside it. `util/helper.py` — the rule itself — was never patched.

## 2. The baseline's own record survives, and qualifies

§7 declared in advance that recovering *that run's* full-precision `stats/val_step0501.json`
would replace the console line by a manifest edit, and that a record only qualifies if it is the
same run. Preflight found it at
`/homes/clll20/deformsplat/results/diva360_finetune/penguin_0217_0239/`, `stats/` mtime
2026-07-22 08:34 — matching the spike:

```
{"psnr": 25.054527282714844, "ssim": 0.9534690976142883, "lpips": 0.05649951100349426, ..., "num_GS": 23548}
```

It qualifies: the values round to the console line exactly, and its step-0 triple is bit-identical
to all eight sweep rows. The row is now bound to the record and the rounding intervals collapse.
**The baseline was not re-run** — that is prohibited by §7, and the recovery is a sharpening of
the same run, not a substitution.

The disqualified local copy §7 warned about in advance is still there and still disqualified:
`~/results/diva360_finetune/penguin_0217_0239/` (2026-06-24, 25.0107) does not round to the
console line, so it is a different run.

## 3. Room to run

Compute was available (four idle GPUs, the pinned image `clll20/deformsplat:sweep-20260705`
present, four unrelated `trex` containers running), and the two runs took roughly 9.5 minutes
each, sequentially.

## 4. Observations that change how the remaining work executes

These are the reason this addendum exists rather than a line in the handoff.

**The penguin run console logs are gone and are unrecoverable.** Nine of them were destroyed by
an earlier container removal. Consequence: the ρ = 32 and ρ = 64 **launch commands were
reconstructed** from the archived `hare me` form for the other asset (`trex`), substituting the
penguin data directory, checkpoint and object name — they were not recovered from a penguin log.
The reconstruction is validated by outcome rather than by provenance: both runs produced a step-0
triple bit-identical to all seven archived rows, which is the comparability gate's own test of
whether the same weights were scored by the same camera on the same data. The launch lines as
actually issued are recorded at the head of
[`penguin_rho32.log`](../../cluster/rho_probe_evidence/_logs/penguin_rho32.log) and
[`penguin_rho64.log`](../../cluster/rho_probe_evidence/_logs/penguin_rho64.log), together with
both source hashes, so future work reads them from a log rather than reconstructing them again.

**The scratch filesystem is at 99% and its mount expires.** `/mnt/fast0` stood at 1.7 T of 1.8 T
with ~26 GB free, and `/mnt/fast0/clll20` expires **2026-08-26**. `/homes/clll20`, which holds the
sources and the `results/` tree everything above was read from, is **permanent**. Consequence:
anything still wanted off the node should be fetched before late August, and no plan should assume
scratch space for a large re-run. Nothing outstanding in Plan 1 needs either.

**The cluster working tree is dirty against a head commit from December 2025** (`60955d6`,
2025-12-02), with seven modified files and a long untracked list including a
`deform_splat.py.prebak`. Consequence: a commit id is not a usable identifier for this tree, which
is why every claim in the record keys on **content hashes** instead. The six files that matter are
captured by hash above.

## 5. Ticket bearing

This addendum plus the archived transcript are what close the preflight ticket. The four
observations in §4 are findings about the apparatus, not deviations from
[plan1_prereg.md](plan1_prereg.md) — none of them changed a declared rule, a threshold, or a
published number. How each declared branch actually resolved is recorded in §10 of that document.
