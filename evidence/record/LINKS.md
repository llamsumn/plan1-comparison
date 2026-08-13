# Where these records' links go

## The five documents in this directory

| document | what it is |
|---|---|
| `plan1_prereg.md` | the pre-registration: the saturation rule, the comparability gate and the precision policy, declared before preflight and before the runs they select |
| `plan1_verdict.md` | the verdict: how every declared branch actually resolved, including the one post-hoc edit, disclosed with its diff |
| `trex_comparison_prereg.md` | the **second** table's pre-registration: trex's own replicate-band rule, baseline gate values, saturation branches and numbered prediction, declared before the baseline arm ran. It *binds to* `plan1_prereg.md` for everything it inherits rather than restating it |
| `phase_b_probe_verdict.md` | the Phase-B ρ-probe verdict, which the pre-registration names as its companion — the feasibility finding, with the two carve-outs the pre-registration's §6 exists to close |
| `plan1_feasibility_addendum.md` | the feasibility addendum, which the verdict names for its first claim: 6/6 source hashes matched, so the wiring evidence transfers to the archived rows |

The first three govern a published table — two of them the penguin's, the third trex's.
The last two are the documents the first two cite by name, and they are here so that
those citations resolve.

## Why this note exists

All five are **vendored byte-exact**. Their internal links
were written where the documents were written, and several of them point at paths that
do not exist here — either because the target sits under `evidence/` in this repository
and not at the root, or because the target is a planning document that deliberately did
not travel.

**No link has been rewritten, and no byte under `evidence/` has been edited.** That is
the whole reason the copies are worth having: each one is pinned by sha256 in
`evidence/PROVENANCE.toml`, so anyone holding an original can audit this copy against
it. A rewritten link would change the bytes and cost exactly that. A dangling link is
the smaller price — provided it is *accounted for*, which is what this note is.

Every relative link in every document here is one of three things:

1. it resolves as written — 3 targets, over 12 link instances;
2. it is a **redirect**: the target is in this repository, under a different path — 8
   targets, over 12 instances;
3. it is an **exclusion**: the target is a document that did not travel, and the entry
   below says what it was and why — 11 targets, over 20 instances.

That is 44 links in all, and `test_the_note_is_not_vacuous` reads all six of those
numbers back out of this paragraph and recounts them against the documents. It does,
because two of them were wrong when this note was first written.

`tests/test_vendored_record_links.py` walks all five documents and fails if a link is
none of the three. So this note cannot go stale against the records: a document added
here, or a link nobody classified, fails the suite rather than reaching a reader as a
404. Vendoring the trex pre-registration is what that guard was written for — it
arrived carrying fifteen links of its own, ten of them to targets that are not here,
and every one had to be classified before it could ship.

Two of the three resolving targets resolve **because of this work**. The
pre-registration cites the Phase-B probe verdict as its companion, and the verdict cites
the feasibility addendum for its first claim; both citations pointed at siblings that
were not here. Placing those two documents in this directory is what made them resolve —
no link edited, no hash disturbed.

## Redirects — the target is in this repository, at another path

Each of these was written as `../../…`, which reached the root of the directory the
documents were authored in. Here, the same content sits under `evidence/`.

| link as written | where it is in this repository |
|---|---|
| `../../cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt` | `evidence/cluster/rho_probe_evidence/_logs/plan1_preflight_20260805.txt` — the preflight transcript, in full |
| `../../cluster/sources_20260805_patched` | `evidence/cluster/sources_20260805_patched/` — the patched call site the ρ = 32 and ρ = 64 runs went through |
| `../../cluster/sources_20260805_patched/deform_splat.py` | `evidence/cluster/sources_20260805_patched/deform_splat.py`, sha256 `e2ca10cf…`, the value the manifest cites and the wiring harness parses |
| `../../cluster/rho_probe_evidence/_logs/penguin_rho32.log` | `evidence/cluster/rho_probe_evidence/_logs/penguin_rho32.log` — the ρ = 32 console, launch line and both source hashes at its head |
| `../../cluster/rho_probe_evidence/_logs/penguin_rho64.log` | `evidence/cluster/rho_probe_evidence/_logs/penguin_rho64.log` — the ρ = 64 console, likewise |
| `../../cluster/rho_probe_evidence/trex_vanilla` | `evidence/cluster/rho_probe_evidence/trex_vanilla/` — the mechanism-off trex run, `null` row of the second table and one of the three the replicate band is derived from |
| `../../cluster/rho_probe_evidence/trex_rho1a` | `evidence/cluster/rho_probe_evidence/trex_rho1a/` — unit-rigidity replicate a, second of the three |
| `../../cluster/rho_probe_evidence/trex_rho1b` | `evidence/cluster/rho_probe_evidence/trex_rho1b/` — unit-rigidity replicate b, third of the three |

The last three are the run directories the trex pre-registration's §3 names as the
source of a band it deliberately does not state a value for. They are here in full, as
the `stats/val_step0000.json` and `stats/val_step0501.json` the assembler actually
reads — so the one number that document declines to write down can be recomputed from
this repository alone.

## Exclusions — the document did not travel

Records travel; plans do not. Each entry says what the document was and why it stayed
behind, so that a reader can tell a reasoned exclusion from a gap. In every case the
part that is load-bearing for a claim in these records is *already here*, either quoted
inside the vendored document or present as evidence.

| link as written | what it was, and why it is not here |
|---|---|
| `../../docs/specs/plan-1-comparison-assembly-spec.md` | The assembly spec — the planning document that sequenced this work, 467 lines. Superseded by its own outputs: the pre-registration and the verdict it called for are vendored here in full. What it decided that still binds — the comparability gate, the precision policy, the saturation rule — is stated in `CONTEXT.md` and asserted in the suite rather than described. Shipping superseded planning material into a submission artefact invites a reader to spend their attention reconciling the plan with what shipped. |
| `../../docs/specs/penguin-deformsplat-comparison-spec.md` | The parent specification, 402 lines, and superseded on the same argument. Its published gap-recovered cells are the one part anything here still rests on, and they are carried as data in `tests/conftest.py` (`PARENT_CELLS`) — which is also where the retracted correction is now checked, interval against interval. |
| `phase_b_plan.md` | The executable plan the Phase-B probe verdict judges. It cites code by line number in a working clone at an absolute path under the author's home directory, so vendoring it would carry back in exactly the defect this repository removed. The part that is load-bearing — the T0 gate it declared before any run, and its `Fail ⇒ wiring bug ⇒ STOP and fix` wording — is quoted verbatim in the verdict, where it is used to record the gate as missed rather than passed. |
| `deformsplat_api_map.md` | Phase A's reconnaissance of the DeformSplat API and the injection-seam decision, with the same absolute-path citations. The seam it recommended is the one that shipped, and both ends of it are here: the rule at `box_b/edge_weights.py`, and the deployed call site under `evidence/cluster/`. |
| `verdict.md` | A curated collection of verdicts across several phases, which states on its own first page that it is **not canonical** and points onward to two further documents that are also not here. Its Phase-B line is the verdict vendored beside this note. |
| `plan1_cluster_handoff.md` | The handoff that dispatched preflight and the two saturation runs, as pasteable commands, because the authoring environment had no non-interactive credential for the node. Its output returned as the feasibility addendum, which *is* vendored here; the launch lines it produced are at the head of the two run logs, recorded there so that nothing has to reconstruct them again. |
| `phase_c_plan.md` | The Phase-C pilot plan, which selected the two objects and ran the 2026-07-26 sweep that produced six of the seven trex rows. Cited three times by the trex pre-registration — for the frame range behind `trex_0135_0250`, for the PCA aspect ratios behind §8's bar-vs-blob prediction, and for the near/far concentration crossing. All three are *quoted with their numbers* at the point of citation, which is where they do their work; the plan itself is planning material of the kind superseded by its own outputs. |
| `trex_baseline_gate.md` | The record of the native baseline run — its gate result, its launch command, its config dump and its six inline source hashes. **The strongest exclusion in this table, and the only one where the load-bearing content is present as evidence rather than as a quotation.** Its four gate values are pinned in `tests/test_trex_assembly.py` as `GATE_START` and `GATE_PRIMITIVES` and checked against the vendored `baseline_trex_0135_0250` run record itself, so a reader does not have to take the document's word for the match — the assembler's comparability gate re-establishes it from the JSON on every run. The document also cites the node's own `SETUP.md`, its two run logs and the cluster account's home paths, so vendoring it would import a fresh set of dead links and the private paths this repository exists to be free of. |
| `trex_checkpoint_provenance.md` | The investigation that settled the 17,779-vs-33,623 question: `ckpt_best_psnr.pt` was written at training step 2999 with 17,779 primitives while training ran on, so the two counts are two moments of one run rather than a discrepancy. Cited by §4.1. Its conclusion is load-bearing and is *here as evidence* rather than as prose — 17,779 is the primitive count the comparability gate enforces across all seven rows, and `test_the_gate_raises_when_a_row_arrives_from_a_different_primitive_count` drives the gate against 33,623 to watch it refuse. |
| `plan_decisions_2026-08-11.md` | The decision log that designated publication of the second table as the first thing to cut if the calendar tightened, cited by §7 for that designation. It records a contingency that was not taken: the cut was declined and the second table is in `out/`. It is a workbench planning document besides, of the kind two entries above are excluded as. |
| `../item2_mask/trex_roughness_prereg.md` | The pre-registration for the trex **roughness-slope** diagnostic, cited by §1 in order to put it explicitly *out* of scope. It governs a different result on the same asset, and the citation exists to stop the two being read as one: that work moved a boundary to `n = 2` for the roughness slope only, where this chain delivers `n = 2` on the comparison table. Neither carries the other. Nothing in this repository rests on it, which is why keeping it out costs nothing — and why the citation is worth having anyway. |

## Why not simply vendor the eleven as well

Because the recursion has to stop somewhere, and the honest place to stop is at the
documents these records *argue from* rather than the ones they were planned by. Several
carry absolute paths under a home directory, which is the defect this repository
exists to remove; several are superseded by outputs that are here in full; and each of
the eleven links onward to documents of its own, so vendoring them would produce a fresh
set of dead links to classify rather than close this one.

The five added with the trex pre-registration make the rule easier to state than the
original six did, because they split so cleanly. Three are planning material —
`phase_c_plan.md`, `plan_decisions_2026-08-11.md`, and the roughness pre-registration
that §1 cites in order to exclude. The other two are genuine **records**, and records
are the category that normally travels: `trex_baseline_gate.md` and
`trex_checkpoint_provenance.md`. They stay out because what they establish is here in a
stronger form than a copy of the document would be — the four gate values and the
17,779-primitive count are not quoted from them but *enforced* against the vendored run
records by the assembler's comparability gate, with a test driving that gate against
33,623 to watch it refuse. A vendored document says a check was done. A gate that
re-runs on every `pytest` says it still holds.

What is defended instead is that every citation in these records now leads *somewhere*:
to the file, or to this note.
