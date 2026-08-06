# penguin_0217_0239 — imposed rigidity against the DeformSplat baseline

_Assembled 2026-08-06 by `plan1.assemble` from the manifest at `manifests/penguin_deformsplat.toml`. Every number below traces to a named run; see Provenance. Rules pre-registered in `all_record/deformsplat_corroboration/plan1_prereg.md`._

| rigidity source | information used | PSNR | SSIM | LPIPS |
|---|---|---|---|---|
| *shared start (step 0)* | — | 16.764 | 0.9060 | 0.1020 |
| none (grouping off, unit rigidity) | — | 19.277 | 0.9199 | 0.0916 |
| imposed, ρ = 0.25 | static asset + one handle | 17.906 | 0.9053 | 0.1059 |
| imposed, ρ = 4 | static asset + one handle | 22.104 | 0.9382 | 0.0697 |
| imposed, ρ = 16 | static asset + one handle | 22.953 | 0.9443 | 0.0634 |
| imposed, ρ = 32 | static asset + one handle | 21.828 | 0.9385 | 0.0701 |
| imposed, ρ = 64 | static asset + one handle | 20.739 | 0.9306 | 0.0776 |
| inferred groups (baseline, as published) | observed before/after motion | 25.055 | 0.9535 | 0.0565 |
| **fraction of the gap recovered** (at imposed, ρ = 16) | | 63.6% | 72.6% | 80.4% |

**Saturation rule — SATURATED.** saturated: the curve has turned over — rho=64 falls 1.0889 dB below its predecessor. Smallest rigidity within the band of the maximum (22.9534 dB at rho=16) is rho=16.

**Full imposed sweep** (selection is disclosed, not hidden):

| ρ | role | PSNR |
|---|---|---|
| 0.25 | imposed | 17.906 |
| 1 | null_replicate | 19.361 |
| 1 | null_replicate | 19.277 |
| 4 | imposed | 22.104 |
| 16 | imposed | 22.953 |
| 32 | imposed | 21.828 |
| 64 | imposed | 20.739 |

**The no-rigidity configuration was run 3 times** (PSNR 19.277, 19.361, 19.277); replicate band **0.0841 dB**, derived from `vanilla`, `rho1a`, `rho1b`.

## Limitations

- The no-rigidity row is the mechanism-off run alone. Its equivalence to the unit-rigidity runs rests on code inspection — the scaling helper early-returns its input at unit rigidity — and not on measurement: the gate that would have established it end to end is the one that failed.
- The replicate band was measured at unit rigidity. Applying it across the sweep assumes replicate noise does not grow with rigidity; this is an assumption, not a measurement.
- Single asset, single evaluation camera, single seed per setting. Nothing here establishes that the result generalises to another object.
- The baseline observes the object's motion; this method does not. Exceeding it on reconstruction fidelity is not a goal and is not claimed.

## Provenance

Evaluation step 501; 23548 primitives in every row.

| row | source |
|---|---|
| `vanilla` | vanilla: evidence/cluster/rho_probe_evidence/penguin_vanilla/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_vanilla/stats/val_step0000.json |
| `rho1a` | rho1a: evidence/cluster/rho_probe_evidence/penguin_rho1a/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho1a/stats/val_step0000.json |
| `rho1b` | rho1b: evidence/cluster/rho_probe_evidence/penguin_rho1b/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho1b/stats/val_step0000.json |
| `rho025` | rho025: evidence/cluster/rho_probe_evidence/penguin_rho025/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho025/stats/val_step0000.json |
| `rho4` | rho4: evidence/cluster/rho_probe_evidence/penguin_rho4/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho4/stats/val_step0000.json |
| `rho16` | rho16: evidence/cluster/rho_probe_evidence/penguin_rho16/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho16/stats/val_step0000.json |
| `rho32` | rho32: evidence/cluster/rho_probe_evidence/penguin_rho32/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho32/stats/val_step0000.json |
| `rho64` | rho64: evidence/cluster/rho_probe_evidence/penguin_rho64/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/penguin_rho64/stats/val_step0000.json |
| `baseline` | baseline: evidence/cluster/rho_probe_evidence/baseline_penguin_0217_0239/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/baseline_penguin_0217_0239/stats/val_step0000.json |

| artefact | identity |
|---|---|
| reference rule (`box_b/edge_weights.py`) | `sha256 38e1a661ded4552e…` |
| method repository HEAD | `ede5fd3a1dda0b69ddb38648c0c97a77021021b0` |
| deployed rule (`cluster/sources_20260729/helper.py`) | `sha256 e83bb80d99e725b7…` |
| patched call site, ρ = 32/64 rows (`cluster/sources_20260805_patched/deform_splat.py`) | `sha256 e2ca10cf4ef7ae00…` |
