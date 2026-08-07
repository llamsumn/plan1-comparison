# Third-party material

This repository redistributes work that is not its own. This file is the record of
what, from where, under what terms, and — where it was changed — exactly how.

`LICENSE` at the root covers the work authored here. Nothing in this file is covered
by it.

Two rules govern how attribution is placed, and both are deliberate:

**Attribution sits beside the third-party files, never inside them.** Everything under
`evidence/` is pinned by sha256 in `evidence/PROVENANCE.toml` and read back out by AST
in `tests/test_conformance.py` and `tests/test_wiring_assertion.py`. Inserting a
licence header into one of those files would change its hash, break the manifest
citation, break the wiring harness, and destroy the property that makes the vendored
evidence auditable against the archive it was copied from. So the notices live here and
under `third_party/`, and the copied bytes stay exactly as they were deployed.

**Copies live inside `evidence/` with a provenance row; authored files live outside
it.** This file, `LICENSE`, and everything under `third_party/` are authored or
assembled here, so they sit at the repository root where
`tests/test_vendored_evidence.py` does not require a row for them.

---

## DeformSplat — Apache License 2.0

| | |
|---|---|
| project | DeformSplat |
| upstream | `github.com/vision3d-lab/deformsplat` |
| commit | `60955d67d066a8b26e1ed8a92f1c51c902a9ccab` (2025-12-02) |
| paper | Kim et al., *Rigidity-Aware 3D Gaussian Deformation from a Single Image*, SIGGRAPH Asia 2025 — arXiv:2509.22222. "DeformSplat" is the framework name |
| licence | Apache License 2.0 — full text at `third_party/deformsplat/LICENSE` |
| upstream `NOTICE` | none exists at that commit, so Apache-2.0 §4(c) does not apply |

### What is redistributed

Two source files, copied verbatim as deployed on the cluster, 1,581 lines together:

| file here | upstream path | lines |
|---|---|---|
| `evidence/cluster/sources_20260729/helper.py` | `util/helper.py` | 637 |
| `evidence/cluster/sources_20260805_patched/deform_splat.py` | `deform_splat.py` | 944 |

They are here as **evidence, not as a dependency**. Nothing in this repository imports
either one; both are read as *text* — the conformance suite loads the deployed rigidity
rule by AST and drives it against this project's own reference implementation, and the
wiring harness parses the in-run assertion block out of the call site. They import
`simple_trainer`, `jhutil` and `util.mini_pytorch3d`, none of which are here, so neither
file is runnable in this repository and neither is meant to be.

### Both files carry a local modification

Apache-2.0 §4(b) asks that modified files carry prominent notices stating they were
changed. Those notices cannot go in the files themselves without breaking the hash
chain described above, so they are carried here instead — and rather than a bare
statement that something changed, the **complete diff against the pinned upstream
commit** is committed:

| diff | change |
|---|---|
| `third_party/deformsplat/helper.py.diff` | **+19 lines**, one hunk, appended at end of file: `partition_anchors_by_handle` and `rho_scale_weights` |
| `third_party/deformsplat/deform_splat.py.diff` | **+11 lines**, one hunk at the `weight` tensor: the ρ injection and the T0.1a/b/c in-run assertion block |

**30 lines in total.** Both diffs apply cleanly to the pinned upstream commit, and
`tests/test_upstream_diff.py` asserts that every added line appears verbatim in the
deployed file and every removed line does not, so a diff cannot drift away from the
source it claims to describe.

What the diffs establish, and the reason they are worth committing: **the ARAP
formulation, the linear blend skinning, the solver and the optimiser are untouched.**
The injection sits between `rbf_weight` and the drag loop and scales one tensor. That
is a claim a reader can check in thirty seconds rather than take on trust.

`deform_splat.py.diff` carries a **second hunk that is not this project's change** —
`{"step": step}` → `{"step": drag_iterations}`. It is already present in
`deform_splat.py.prebak`, taken before the ρ patch was applied, so it arrived with the
clone. It writes checkpoint metadata only, and no published number reads the checkpoint:
the table reads `stats/val_step*.json`. It is disclosed rather than dropped, because a
diff that omits a real difference is not a diff.

### Bibliography entry

Repository, commit, licence, venue and arXiv id were each checked against the source.
The author list is taken from the project's existing bibliography entry, which was
compiled against the same arXiv id and carries a full author list rather than a
placeholder — so it is transcribed, not guessed. The venue is still flagged for
confirmation there and that flag is carried over rather than dropped.

```bibtex
@inproceedings{kim2025deformsplat,
  author    = {Kim, Jinhyeok and Bang, Jaehun and Seo, Seunghyun and Joo, Kyungdon},
  title     = {Rigidity-Aware 3D {G}aussian Deformation from a Single Image},
  booktitle = {SIGGRAPH Asia 2025 Conference Papers},
  year      = {2025},
  note      = {Framework name: DeformSplat. arXiv:2509.22222. Code:
               \url{https://github.com/vision3d-lab/deformsplat}, Apache-2.0.
               VERIFY final venue details}
}
```

---

## DiVa360 — MIT License

| | |
|---|---|
| dataset | DiVa360: The Dynamic Visual Dataset for Immersive Neural Fields |
| upstream | `github.com/brown-ivl/DiVa360` |
| paper | CVPR 2024 (Highlight) |
| licence | MIT — permits redistribution with attribution |

### What is redistributed

`data/penguin_original.ply` — 5.6 MB, 23,548 Gaussians. It is **not a DiVa360 file**:
it is a 3D Gaussian Splatting export of a checkpoint trained on DiVa360's `penguin`
sequence (`penguin_0217`, evaluated against frame `penguin_0239`), which is why the
run logs under `evidence/cluster/` name `data/diva360_processed/penguin_0239/` and
`results/diva360/penguin_0217/`. The underlying captured data is DiVa360's, and the
attribution is owed on that basis.

**The 3DGS checkpoint was not trained by this project.** It came with the cluster
image, and reusing it rather than training it is recorded in the archive's
`cluster/SPIKE_VERDICT.md`. Nothing in this repository claims otherwise, and nothing in
the published table depends on how it was produced — the comparison is between arms
that all start from the identical step-0 state, which is asserted rather than assumed.

The asset is tracked by exception against the `*.ply` ignore rule; `.gitignore` records
why, and `evidence/PROVENANCE.toml` carries its `[[ported]]` row and its dataset
attribution.

### Bibliography entry

**Unlike the DeformSplat entry, this one is not verified.** Nothing on this machine
carries a DiVa360 author list, so it is left as an explicit placeholder rather than a
plausible guess: an unverified citation that looks finished is worse than one that
announces itself, and this project already carries proof of that (`luo2024gesi`, a
self-flagged placeholder that survived into cited text). It is filled from the upstream
`README` before anything cites it.

```bibtex
@inproceedings{diva360,
  title     = {{DiVa-360}: The Dynamic Visual Dataset for Immersive Neural Fields},
  author    = {TODO-VERIFY-AUTHORS},
  booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and
               Pattern Recognition (CVPR)},
  year      = {2024},
  note      = {Highlight. Data: \url{https://github.com/brown-ivl/DiVa360}, MIT}
}
```

---

## The ported method

`arap_core/`, `box_b/edge_weights.py`, `examples/run_penguin.py` and the solver
diagnostic under `diagnostics/` were ported from this project's own repositories, not
from a third party. They are the same author's work under the same `LICENSE`, and their
source repository, source commit and sha256 are recorded per file under `[[ported]]` in
`evidence/PROVENANCE.toml`.
