# KGAMMA VERDICT — GREEN

**GATE: GREEN — mask intervention (supervisor's item 2) UNBLOCKED**

_Pure-ARAP + distance-weighted RBF, synthetic bar/blob. Recomputed from CSVs and asserted (11/11 checks pass). Generated 2026-07-19. Every claim pending DeformSplat cluster corroboration._

## Three-panel result

| panel | regime | K (live) | γ (live) | support_norm |
|---|---|---|---|---|
| bar × bar_bend | **global** (86 global / 18 gated / 4 γ20-seed1 boundary) | — | — | undefined (whole-object) |
| bar × static_far | contained | **inert** (K@γ flat) | **flat** | 0.215 (range 0.0005 < spread 0.0011) |
| blob × static_far | contained | **inert** (K@γ flat) | **flat** | 0.185 (range 0.0004 < spread 0.0026) |
| blob × bar_bend | **N/A** (edit undefined on compact geometry) | — | — | — |

## Kernel structure (Step 2 — the squash is gone)
- Live band γ=1–5 unfloored: median edge weight **0.50→0.031** (**16×**), w̄ 0.52→0.10.
- Floor-onset γ=20 (29% floored at low K) · gated γ=50 (80% floored). No [0.88,1.0] high-band squash — that was the retired bbox-scale bug. "Dead kernel" at high γ **is** the floor, caught by the degeneracy gate.

## Insight

> In the clean live-kernel regime (γ=1–5, unfloored), realised support is **flat vs both K and γ on both geometries** — bar ≈ 0.215, blob ≈ 0.185 — across a 16× change in kernel breadth. K is inert on both geometries; the only `responds` verdicts (5, all bar/static_far) are a ~2% floor-onset shift at γ=20 that **dissolves when the live band is isolated** (`gamma_live@K` 12/12 flat). The sole systematic structure is a **fixed per-geometry support offset set by boundary conditions and geometry** (bar 0.215 vs blob 0.185). **Therefore edit scope is not reliably hand-tunable via the distance-weighted KNN graph** — which motivates a predicted scope field (the estimator) over hand-tuned graph hyperparameters.

## Green-light gate — criteria
- **(a) regime split confirmed on the bar** — bar_bend global (live-band resid 1.36–1.71 > 1.0), static_far contained. ✓
- **(b) kernel structure consistent** — three-regime; no squash; scale-bug retired; dead-kernel = floor at high γ. ✓
- **(c) contained K/γ flat & seed-consistent** — explained by boundary conditions + geometry (fixed offset), across-γ range < seed spread. ✓

All three hold → the original `bar_bend`/`static_far` γ-disagreement is **fully explained** (decay_length railing in the global regime **plus** the γ=20 kernel floor — both artifacts, both dissolved by the bounded metric + live-band isolation).

## Measurement limitations & reconciliations (§6.5)
1. **Red-light disagreement resolved:** `bar_bend` "responding to γ" under `decay_length` was the metric railing in a whole-object-motion regime plus the γ=20 floor; under the bounded metric it is `bar_bend` = global (support undefined) and `static_far` = flat. The contradiction dissolves.
2. **A manufactured signal retired:** the `decay_length` "blob K responds at γ=5, ratio 2.17" does **not** survive the bounded metric (`blob/static_far/K@gamma` flat, ratio ≈ 0.48–0.56) — a concrete case of a saturating metric inventing a signal; the motivating example for the bounded metric. K is inert on both geometries.
3. **`nan`-ratio edge case (Fix A):** an un-arbitrable sweep (all swept values single-seed) fell open to `responds`; now guarded to `insufficient`. Classifier robustness note; total `responds` 6→5.

## Assertion log

| check | result | recomputed |
|---|---|---|
| S1 bar_bend regimes = 86 global / 18 degenerate / 4 contained | PASS | {'global': 86, 'contained': 4, 'degenerate': 18} |
| S1 the 4 contained bar_bend cells are all γ=20, seed=1 | PASS | [(4, 20.0, 1), (8, 20.0, 1), (12, 20.0, 1), (16, 20.0, 1)] |
| S1 bar_bend live-band residual_fraction ≈ 1.36–1.71 (> τ_regime) | PASS | [1.360, 1.709] |
| S1 bar_static_far live band all contained | PASS | Counter({'contained': 72}) |
| S2 median weight γ=1→5 ≈ 0.50→0.03 (≈16×, no high-band squash) | PASS | γ1 med=0.498, γ5 med=0.031, ratio=16.3×; w̄ γ1=0.52→γ5=0.10 |
| S3 bar static_far live-band mean ≈ 0.215 each (±0.005) | PASS | {1.0: 0.215, 2.0: 0.2149, 3.0: 0.2147, 5.0: 0.2145} |
| S3 blob static_far live-band mean ≈ 0.185 each (±0.005) | PASS | {1.0: 0.1844, 2.0: 0.1846, 3.0: 0.1847, 5.0: 0.1848} |
| S3 across-γ range ≪ within-γ seed spread (both geometries → flat) | PASS | bar range=0.0005 vs spread=0.0011; blob range=0.0004 vs spread=0.0026 |
| S3 gamma_live@K = 12/12 flat | PASS | 12/12 flat |
| S3 responds = 5, all bar/static_far/gamma@K (γ=20-driven) | PASS | [('bar', 'gamma@K', '4'), ('bar', 'gamma@K', '6'), ('bar', 'gamma@K', '8'), ('bar', 'gamma@K', '12'), ('bar', 'gamma@K', '16')] |
| S3 blob K@gamma flat at every live γ (Fix-B reversal holds) | PASS | [('1.0', 'flat', '0.4813'), ('2.0', 'flat', '0.5339'), ('3.0', 'flat', '0.5611'), ('5.0', 'flat', '0.5021')] |
