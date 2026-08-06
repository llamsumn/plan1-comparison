# FIGURE_CHECK — §6.2 dead-vs-live + regime-U

**ALL PASS — 9/9 checks.** Every plotted value re-derived from `kgamma_summary.csv` / `mask_grid.csv` and cross-checked against `KGAMMA_VERDICT.md` + `MASK_VERDICT.md`. Figures: `fig_62_dead_vs_live.png` (+pdf), `fig_62_regime_u.png` (+pdf).

## Assertion log

| check | result | recomputed |
|---|---|---|
| 1. Figure A points re-derived from source CSV (0 mismatches) | PASS | 60/60 points match |
| 2a. item-1 means bar≈0.215 / blob≈0.185 (KGAMMA_VERDICT) | PASS | bar=0.2148, blob=0.1846 |
| 2b. item-2 δ=0 series matches MASK_VERDICT A2 (bar) | PASS | [0.2191, 0.2167, 0.2147, 0.2114, 0.2072, 0.1988] |
| 2c. item-2 δ=0 series matches MASK_VERDICT A2 (blob) | PASS | [0.1885, 0.1868, 0.185, 0.1817, 0.1793, 0.1777] |
| 2d. ρ=1 anchors 0.2147 / 0.1850 (MASK_VERDICT A1) | PASS | bar=0.2147, blob=0.1850 |
| 2e. A2 ratio/rel% match verdict (bar 14.6×/9.5%, blob 4.4×/5.8%) | PASS | bar 14.61×/9.5%, blob 4.44×/5.8% |
| 2f. regime counts 41 contained / 49 global (MASK_VERDICT A6) | PASS | {'contained': 41, 'global': 49} |
| 3. Figure A shared y-limits asserted in generator | PASS | ylim=(0.1691, 0.2261) (identical L/R by assert) |
| 4. Exclusion audit reconciles to grid totals (41/49) | PASS | contained=41, global=49 over 90 cells |

## Exclusion audit

- Figure A-left excludes γ ∈ [20.0, 50.0] (γ=20 floor-onset, γ=50 gated) — plotted γ = [1.0, 2.0, 3.0, 5.0].
- ρ=0.25: 13/15 contained (2 global) — CONTAINED extreme.
- ρ=0.5: 0/15 contained (15 global) — global middle.
- ρ=1: 0/15 contained (15 global) — global middle.
- ρ=4: 0/15 contained (15 global) — global middle.
- ρ=16: 13/15 contained (2 global) — CONTAINED extreme.
- ρ=64: 15/15 contained (0 global) — CONTAINED extreme.

## fig_62_dead_vs_live render note

2026-07-20: right-panel bar annotation repositioned — it previously clipped the
right-hand y-tick labels. Annotation clip fixed, data unchanged, checks re-passed
(9/9, 60/60 points re-derived from source CSVs).

## fig_62_regime_u palette note

Note: green tile colour is a deliberate categorical departure from the item-1 continuous
palette — regime is a categorical outcome, not a continuation of the K×γ colour scale.
Not an inconsistency.

## Shared-axis note

`make_62_figures.make_figure_a` asserts `ax_left.get_ylim() == ax_right.get_ylim()` before saving — the shared `support_norm` ruler is enforced as a test, not left to convention.
