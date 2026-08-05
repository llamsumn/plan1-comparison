# penguin_0217_0239 — imposed rigidity against the DeformSplat baseline

_Assembled 2026-08-05 by `plan1.assemble` from the manifest at `/Users/kahncant/plan1-comparison/manifests/penguin_deformsplat.toml`. Every number below traces to a named run; see Provenance. Rules pre-registered in `all_record/deformsplat_corroboration/plan1_prereg.md`._

| rigidity source | information used | PSNR | SSIM | LPIPS |
|---|---|---|---|---|
| *shared start (step 0)* | — | 16.764 | 0.9060 | 0.1020 |
| none (grouping off, unit rigidity) | — | 19.277 | 0.9199 | 0.0916 |
| imposed, ρ = 0.25 | static asset + one handle | 17.906 | 0.9053 | 0.1059 |
| imposed, ρ = 4 | static asset + one handle | 22.104 | 0.9382 | 0.0697 |
| imposed, ρ = 16 | static asset + one handle | 22.953 | 0.9443 | 0.0634 |
| inferred groups (baseline, as published) | observed before/after motion | 25.055 | 0.9535 | 0.056 |

**Saturation rule — NOT SATURATED.** not saturated: rho=16 gains 0.8489 dB over its predecessor, exceeding the 0.0841 dB band; continue at rho=32.

> No gap-recovered fraction is published while the sweep is unsaturated. The rule was declared before the runs and is what selects the reported row.

**Full imposed sweep** (selection is disclosed, not hidden):

| ρ | role | PSNR |
|---|---|---|
| 0.25 | imposed | 17.906 |
| 1 | null_replicate | 19.361 |
| 1 | null_replicate | 19.277 |
| 4 | imposed | 22.104 |
| 16 | imposed | 22.953 |

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
| `vanilla` | vanilla: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_vanilla/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_vanilla/stats/val_step0000.json |
| `rho1a` | rho1a: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho1a/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho1a/stats/val_step0000.json |
| `rho1b` | rho1b: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho1b/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho1b/stats/val_step0000.json |
| `rho025` | rho025: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho025/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho025/stats/val_step0000.json |
| `rho4` | rho4: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho4/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho4/stats/val_step0000.json |
| `rho16` | rho16: /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho16/stats/val_step0501.json (step 501), start /Users/kahncant/3D/cluster/rho_probe_evidence/penguin_rho16/stats/val_step0000.json |
| `baseline` | baseline: /Users/kahncant/3D/cluster/spike_logs/phase3_run_console.log:66 (step 501), start /Users/kahncant/3D/cluster/spike_logs/phase3_run_console.log:53 |

| artefact | identity |
|---|---|
| reference rule (`box_b/edge_weights.py`) | `sha256 38e1a661ded4552e…` |
| method repository HEAD | `ede5fd3a1dda0b69ddb38648c0c97a77021021b0` |
| deployed rule (`cluster/sources_20260729/helper.py`) | `sha256 e83bb80d99e725b7…` |
