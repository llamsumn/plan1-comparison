# MASK VERDICT — GREEN

**GATE: GREEN — ρ RESPONDS at δ=0 on both panels; δ responds within ρ≠1 rows (bar 3/5, blob 4/5); pin reading is split across panels ({'bar': 'DIFFERS', 'blob': 'TRACKS'}) — mechanism claim earned only where DIFFERS holds**

_Pure-ARAP, explicit rigid/soft mask (R–R interior ρ-scaling; annulus partition; γ0=5, K0=12, seeds [0, 1, 2]). Recomputed from `mask_grid.csv` and asserted (17/17 checks pass). Generated 2026-07-19. Every claim pending DeformSplat cluster corroboration._

**Box-B consequence (forced by the outcome map):** B predicts a **per-region rigidity field**; the mechanism claim is panel-dependent — state per-geometry, no overreach.

## Headline — the two axes + the discriminator

| panel | ρ main effect at δ=0 (A2) | δ within ρ≠1 rows (A3) | pin (A5) |
|---|---|---|---|
| bar × static_far | **responds** — range 0.0204 (9.5% of anchor), ratio 14.61 | 3/5 rows respond | **DIFFERS** |
| blob × static_far | **responds** — range 0.0108 (5.8% of anchor), ratio 4.44 | 4/5 rows respond | **TRACKS** |
| bar × bar_bend | regime watch: {'contained': 41, 'global': 49} — **global→contained transition (FINDING)** | — | excluded (BC instrument) |
| blob × bar_bend | N/A by construction | — | — |

## A2 — ρ main effect at δ=0 (the headline axis)

| geometry | ρ=0.25 | ρ=0.5 | ρ=1 | ρ=4 | ρ=16 | ρ=64 | range | spread | ratio | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| bar | 0.2191 | 0.2167 | 0.2147 | 0.2114 | 0.2072 | 0.1988 | 0.0204 | 0.0014 | 14.61 | **responds** |
| blob | 0.1885 | 0.1868 | 0.1850 | 0.1817 | 0.1793 | 0.1777 | 0.0108 | 0.0024 | 4.44 | **responds** |

Effect sizes: bar range 0.0204 (**9.5%** of the 0.2147 anchor); blob 0.0108 (**5.8%** of 0.1850). Ratios travel with sizes per the frozen gate.

## A3/A4 — δ within rows + interaction structure

| geometry | ρ | δ-range | rel% | ratio | verdict | monotone in δ |
|---|---|---|---|---|---|---|
| bar | 0.25 | 0.0013 | 0.6% | 2.62 | responds | False |
| bar | 0.5 | 0.0006 | 0.3% | 0.76 | flat | True |
| bar | 4 | 0.0022 | 1.0% | 1.45 | ambiguous | True |
| bar | 16 | 0.0057 | 2.7% | 2.77 | responds | True |
| bar | 64 | 0.0082 | 4.1% | 4.34 | responds | False |
| blob | 0.25 | 0.0052 | 2.8% | 2.05 | responds | False |
| blob | 0.5 | 0.0027 | 1.4% | 1.05 | ambiguous | False |
| blob | 4 | 0.0057 | 3.2% | 2.31 | responds | True |
| blob | 16 | 0.0108 | 6.0% | 4.54 | responds | True |
| blob | 64 | 0.0143 | 8.0% | 6.32 | responds | True |

- bar: δ-range grows with |log ρ| (corr 0.99); ρ=1 row is the identity (bit-identical, A1) — the δ-effect is a **δ×ρ interaction**, as pre-stated in the corrected confound logic.

- blob: δ-range grows with |log ρ| (corr 0.99); ρ=1 row is the identity (bit-identical, A1) — the δ-effect is a **δ×ρ interaction**, as pre-stated in the corrected confound logic.

## A5 — pin discrimination (rigidity vs anchoring)

Thresholds pre-committed before pin data existed: TRACKS iff Pearson r ≥ 0.8 AND pin/mask range ratio ∈ [0.5, 2.0]; panel reading = 2-of-3 ρ rows.

| geometry | ρ row | r(Δpin, Δmask) | range ratio (pin/mask) | tracks? |
|---|---|---|---|---|
| bar | 4 | -1.00 | 10.31 | False |
| bar | 16 | -0.97 | 4.02 | False |
| bar | 64 | -0.79 | 2.77 | False |
| blob | 4 | 0.98 | 3.63 | False |
| blob | 16 | 0.99 | 1.92 | True |
| blob | 64 | 1.00 | 1.46 | True |

- **bar: DIFFERS.** Pin curve range 0.0228; pin level offset -0.0321 vs the ρ=1 anchor (pin means: [0.1937, 0.1885, 0.1828, 0.1771, 0.1709]).

- **blob: TRACKS.** Pin curve range 0.0208; pin level offset -0.0113 vs the ρ=1 anchor (pin means: [0.1836, 0.1792, 0.1739, 0.1687, 0.1628]).

## A6 — regime accounting

| control | category | n |
|---|---|---|
| mask | contained | 221 |
| mask | global | 49 |
| mask | na_edit_undefined | 90 |
| pin | contained | 30 |
| pin_null | contained | 2 |

**bar × bar_bend global→contained transition detected** at (δ, ρ, seed) = [(-0.04, 0.25, 0), (-0.04, 0.25, 2), (-0.02, 0.25, 0), (-0.02, 0.25, 2), (0.0, 0.25, 0), (0.0, 0.25, 1), (0.0, 0.25, 2), (0.02, 0.25, 0), (0.02, 0.25, 1), (0.02, 0.25, 2), (0.04, 0.25, 0), (0.04, 0.25, 1), (0.04, 0.25, 2), (-0.04, 16.0, 2), (-0.02, 16.0, 0), (-0.02, 16.0, 1), (-0.02, 16.0, 2), (0.0, 16.0, 0), (0.0, 16.0, 1), (0.0, 16.0, 2), (0.02, 16.0, 0), (0.02, 16.0, 1), (0.02, 16.0, 2), (0.04, 16.0, 0), (0.04, 16.0, 1), (0.04, 16.0, 2), (-0.04, 64.0, 0), (-0.04, 64.0, 1), (-0.04, 64.0, 2), (-0.02, 64.0, 0), (-0.02, 64.0, 1), (-0.02, 64.0, 2), (0.0, 64.0, 0), (0.0, 64.0, 1), (0.0, 64.0, 2), (0.02, 64.0, 0), (0.02, 64.0, 1), (0.02, 64.0, 2), (0.04, 64.0, 0), (0.04, 64.0, 1), (0.04, 64.0, 2)] — itself positive evidence the mask controls scope (pre-registered watch).

## Measurement limitations (§6.5 material)
1. **The pin control bounds the confound; it does not annihilate it.** Pinning is a *hard* boundary condition (positions prescribed), stiffening a *soft* one (weights scaled, positions free). A DIFFERS reading therefore shows rigidity ≠ hard anchoring; a residual soft-anchoring interpretation is bounded, not excluded.
2. **Kabsch–mask interaction:** with a large stiff R the global-rigid removal aligns to R's frame (contract test 6: R residual ≈ 0.22× D), so support reads D's motion relative to R. The ρ=1 identity row anchors the scale.
3. **Pure-ARAP / synthetic scope:** every claim is pure distance-weighted ARAP on synthetic bar/blob, pending DeformSplat cluster corroboration.
4. **ρ=64 convergence:** bar×static_far ρ=64 cells hit max_iters=100 with a monotone energy trace (the probe's known acceptable state) — recorded, not hidden; blob converges. Preflight ruled ρ=64 usable.
5. **Effect sizes are modest in absolute terms** (see A2/A3 rel%): the gate is spread-arbitrated significance, and sizes are quoted alongside every ratio so the reader weighs both.

## Assertion log

| check | result | recomputed |
|---|---|---|
| A1 ρ=1 bit-identical across δ — bar×static_far | PASS | per-seed exact |
| A1 ρ=1 bit-identical across δ — blob×static_far | PASS | per-seed exact |
| A1 ρ=1 bit-identical across δ — bar×bar_bend | PASS | per-seed exact |
| A1 ρ=1 anchor — bar mean ≈ 0.2145 (±0.005) | PASS | mean=0.2147 |
| A1 pin-null equals item-1 anchor — bar | PASS | pin_null=0.21549731455675133 anchor_ref=0.21549731455675133 |
| A1 ρ=1 anchor — blob mean ≈ 0.1848 (±0.005) | PASS | mean=0.1850 |
| A1 pin-null equals item-1 anchor — blob | PASS | pin_null=0.18815710592863463 anchor_ref=0.18815710592863463 |
| A2 ρ main effect at δ=0 — bar classified | PASS | responds: range=0.02037 (9.5% of ρ=1) vs spread=0.00139 ratio=14.61 |
| A2 ρ main effect at δ=0 — blob classified | PASS | responds: range=0.01079 (5.8% of ρ=1) vs spread=0.00243 ratio=4.44 |
| A3 δ within ρ≠1 rows — bar all classified | PASS | 3/5 rows respond: {'0.25': 'responds', '0.5': 'flat', '4': 'ambiguous', '16': 'responds', '64': 'responds'} |
| A3 δ within ρ≠1 rows — blob all classified | PASS | 4/5 rows respond: {'0.25': 'responds', '0.5': 'ambiguous', '4': 'responds', '16': 'responds', '64': 'responds'} |
| A4 interaction — bar δ-range grows with |log ρ| (corr>0) | PASS | corr=0.99; ranges={'0.25': 0.00127, '0.5': 0.00055, '4': 0.00221, '16': 0.00567, '64': 0.00821}; monotone-in-δ={'0.25': False, '0.5': True, '4': True, '16': True, '64': False} |
| A4 interaction — blob δ-range grows with |log ρ| (corr>0) | PASS | corr=0.99; ranges={'0.25': 0.00521, '0.5': 0.00269, '4': 0.00574, '16': 0.01083, '64': 0.01425}; monotone-in-δ={'0.25': False, '0.5': False, '4': True, '16': True, '64': True} |
| A5 pin discrimination — bar: DIFFERS | PASS | per-ρ r/ratio: {'4': (-1.0, 10.31), '16': (-0.97, 4.02), '64': (-0.79, 2.77)}; pin range=0.02277, pin level offset=-0.0321 vs ρ=1 anchor |
| A5 pin discrimination — blob: TRACKS | PASS | per-ρ r/ratio: {'4': (0.98, 3.63), '16': (0.99, 1.92), '64': (1.0, 1.46)}; pin range=0.02082, pin level offset=-0.0113 vs ρ=1 anchor |
| A6 regime accounting complete; bar_bend transition watch evaluated | PASS | bar_bend regimes={'contained': 41, 'global': 49}; global→contained transition=YES — FINDING at [(-0.04, 0.25, 0), (-0.04, 0.25, 2), (-0.02, 0.25, 0), (-0.02, 0.25, 2), (0.0, 0.25, 0), (0.0, 0.25, 1)] |
| A7 figure–CSV cross-check: 0 misrepresentations | PASS | 100 aggregate cells re-derived from CSV == mask_grid.json (figures draw through these same functions); mismatched fields=0 |
