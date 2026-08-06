# PREFLIGHT_REPORT — Phase 3.0

_Generated 2026-07-19T09:55:55._

**Result: PREFLIGHT OK — 324 valid cells to run**

| # | check | kind | result | detail |
|---|-------|------|--------|--------|
| P1 | Imports resolve | HARD | PASS | all import (probe.config → characterisation._shared.config, per spec note) |
| P2 | Seam symbols exist | HARD | PASS | 12 seam symbols present & callable |
| P3 | Locked constants match | HARD | PASS | γ,K,CONDITION_KINDS,τ_floor=0.50 locked; TAU_KERNEL absent |
| P4 | Single degeneracy routing | HARD | PASS | kernel_live, Layer-1 gate, and verifier all route through one is_degenerate object across the gate |
| P5 | Smoke: predictions reproduce | HARD | PASS | all 3 panels reproduce (regime exact, headline within ±5%) |
| P6 | N/A is refused, not run | HARD | PASS | (bar_bend,blob) excluded from valid set and raises when forced |
| P7 | support_norm ∈ [0,1] | HARD | PASS | support_norm ∈ [0,1] on contained smoke cells |
| P8 | Determinism | HARD | PASS | same-seed re-run Δsupport_norm=0.00e+00 (< 1e-12) |
| P9 | Core/probe untouched | HARD | PASS | all 3 write targets under characterisation/; snapshotted 23 core/probe files for post-run compare |
| P10 | Output dir & no clobber | HARD | PASS | existing kgamma_summary.csv will be timestamp-backed-up by the runner |
| P11 | Deps: numpy+scipy | HARD | PASS | numpy✓ scipy✓ |
| P11b | Deps: matplotlib (WARN) | WARN | PASS | matplotlib✓ (Phase 4 need) |

## Reference smoke values (this run)

- `bar/bar_bend` → {'regime': 'global', 'residual_fraction': 1.5684043843974025}
- `bar/static_far` → {'regime': 'contained', 'support_norm': 0.21549731455675133}
- `blob/static_far` → {'regime': 'contained', 'support_norm': 0.18815710592863463}

_Spec note: P1 imports `characterisation._shared.config` in place of the runbook's `probe.config`, which does not exist (the locked grid config lives in `characterisation/_shared/`)._
