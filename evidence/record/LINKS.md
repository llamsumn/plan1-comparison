# Where these records' links go

## The four documents in this directory

| document | what it is |
|---|---|
| `plan1_prereg.md` | the pre-registration: the saturation rule, the comparability gate and the precision policy, declared before preflight and before the runs they select |
| `plan1_verdict.md` | the verdict: how every declared branch actually resolved, including the one post-hoc edit, disclosed with its diff |
| `phase_b_probe_verdict.md` | the Phase-B ρ-probe verdict, which the pre-registration names as its companion — the feasibility finding, with the two carve-outs the pre-registration's §6 exists to close |
| `plan1_feasibility_addendum.md` | the feasibility addendum, which the verdict names for its first claim: 6/6 source hashes matched, so the wiring evidence transfers to the archived rows |

The first two govern the published table. The second two are the documents those two
cite by name, and they are here so that those citations resolve.

## Why this note exists

All four are **vendored byte-exact**. Their internal links
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

1. it resolves as written — 3 targets, over 8 link instances;
2. it is a **redirect**: the target is in this repository, under a different path — 5
   targets, over 9 instances;
3. it is an **exclusion**: the target is a document that did not travel, and the entry
   below says what it was and why — 6 targets, over 12 instances.

That is 29 links in all, and `test_the_note_is_not_vacuous` reads all six of those
numbers back out of this paragraph and recounts them against the documents. It does,
because two of them were wrong when this note was first written.

`tests/test_vendored_record_links.py` walks all four documents and fails if a link is
none of the three. So this note cannot go stale against the records: a document added
here, or a link nobody classified, fails the suite rather than reaching a reader as a
404.

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

## Why not simply vendor the six as well

Because the recursion has to stop somewhere, and the honest place to stop is at the
documents these records *argue from* rather than the ones they were planned by. Three of
the six carry absolute paths under a home directory, which is the defect this repository
exists to remove; two are superseded by outputs that are here in full; and each of the
six links onward to documents of its own, so vendoring them would produce a fresh set of
dead links to classify rather than close this one.

What is defended instead is that every citation in these records now leads *somewhere*:
to the file, or to this note.
