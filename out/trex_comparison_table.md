# trex_0135_0250 — imposed rigidity against the DeformSplat baseline

_Assembled 2026-08-12 by `plan1.assemble` from the manifest at `manifests/trex_deformsplat.toml`. Every number below traces to a named run; see Provenance. Rules pre-registered in `evidence/record/trex_comparison_prereg.md`._

| rigidity source | information used | PSNR | SSIM | LPIPS |
|---|---|---|---|---|
| *shared start (step 0)* | — | 18.715 | 0.8962 | 0.1032 |
| none (grouping off, unit rigidity) | — | 22.615 | 0.9305 | 0.0662 |
| imposed, ρ = 0.25 | static asset + one handle | 20.997 | 0.9188 | 0.0789 |
| imposed, ρ = 4 | static asset + one handle | 24.111 | 0.9390 | 0.0571 |
| imposed, ρ = 16 | static asset + one handle | 22.527 | 0.9288 | 0.0671 |
| inferred groups (baseline, as published) | observed before/after motion | 24.777 | 0.9428 | 0.0541 |
| **fraction of the gap recovered** (at imposed, ρ = 4) | | 69.2% | 69.0% | 74.9% |

**Saturation rule — SATURATED.** saturated: the curve has turned over — rho=16 falls 1.5833 dB below its predecessor. Smallest rigidity within the band of the maximum (24.1106 dB at rho=4) is rho=4.

**Full imposed sweep** (selection is disclosed, not hidden):

| ρ | role | PSNR |
|---|---|---|
| 0.25 | imposed | 20.997 |
| 1 | null_replicate | 22.630 |
| 1 | null_replicate | 22.634 |
| 4 | imposed | 24.111 |
| 16 | imposed | 22.527 |

**The no-rigidity configuration was run 3 times** (PSNR 22.615, 22.630, 22.634); replicate band **0.0193 dB**, derived from `vanilla`, `rho1a`, `rho1b`.

## Limitations

- The no-rigidity row is the mechanism-off run alone. Its equivalence to the unit-rigidity runs rests on code inspection — the scaling helper early-returns its input at unit rigidity — and not on measurement: the gate that would have established it end to end is the one that failed.
- The replicate band was measured at unit rigidity. Applying it across the sweep assumes replicate noise does not grow with rigidity; this is an assumption, not a measurement.
- The wiring discharge BRACKETS these runs rather than pinning them. The archived source snapshot hashes 6/6 to the values recorded in `evidence/record/plan1_prereg.md` §10.1, but it was taken 2026-07-29 — three days after this sweep ran on 2026-07-26 — and the trex sweep consoles carry no inline source hashes, because echoing them inline only began with the 2026-08-05 saturation runs. That the sources were unchanged from 2026-07-29 through the 2026-08-05 preflight is measured; that they were unchanged from 2026-07-26 to 2026-07-29 is not. The penguin's own six sweep rows sit in exactly this position — run 2026-07-25, same snapshot, same three-day gap — and §10.1 accepted the transfer on that basis, so this table is no weaker on this axis than the one it sits beside. The baseline row is the exception and is stronger: its console echoes all six hashes inline.
- Single asset, single evaluation camera, single seed per setting. Nothing here establishes that the result generalises to another object.
- The baseline observes the object's motion; this method does not. Exceeding it on reconstruction fidelity is not a goal and is not claimed.

## Provenance

Evaluation step 501; 17779 primitives in every row.

| row | source |
|---|---|
| `vanilla` | vanilla: evidence/cluster/rho_probe_evidence/trex_vanilla/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_vanilla/stats/val_step0000.json |
| `rho1a` | rho1a: evidence/cluster/rho_probe_evidence/trex_rho1a/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_rho1a/stats/val_step0000.json |
| `rho1b` | rho1b: evidence/cluster/rho_probe_evidence/trex_rho1b/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_rho1b/stats/val_step0000.json |
| `rho025` | rho025: evidence/cluster/rho_probe_evidence/trex_rho025/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_rho025/stats/val_step0000.json |
| `rho4` | rho4: evidence/cluster/rho_probe_evidence/trex_rho4/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_rho4/stats/val_step0000.json |
| `rho16` | rho16: evidence/cluster/rho_probe_evidence/trex_rho16/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/trex_rho16/stats/val_step0000.json |
| `baseline` | baseline: evidence/cluster/rho_probe_evidence/baseline_trex_0135_0250/stats/val_step0501.json (step 501), start evidence/cluster/rho_probe_evidence/baseline_trex_0135_0250/stats/val_step0000.json |

| artefact | identity |
|---|---|
| reference rule (`box_b/edge_weights.py`) | `sha256 d9cbf9014fe8dc30…` |
| deployed rule (`cluster/sources_20260729/helper.py`) | `sha256 e83bb80d99e725b7…` |
| patched call site, echoed by the baseline row's console (`cluster/sources_20260805_patched/deform_splat.py`) | `sha256 e2ca10cf4ef7ae00…` |
