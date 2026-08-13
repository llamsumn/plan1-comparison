"""The second asset, assembled from its own manifest under the same rules.

`trex_0135_0250` is the elongated bar-analog against the penguin's compact blob.
Its rows get their **own** manifest and their own table: the comparability gate keys
on the step-0 triple, the primitive count and the evaluation step, so mixing the two
assets into one manifest would make the gate raise, correctly. Nothing here touches
`manifests/penguin_deformsplat.toml` or the table it publishes.

**What this module is for.** It drives the pre-registered saturation rule on the
trex sweep, pins what the rule returned, and — since the table was published —
pins the fractions the selected row actually recovers and the pre-committed
threshold they were judged against.

The order the tests below were written in is the order that makes the verdict worth
anything, so it is recorded rather than left to be inferred:

1. everything structural first — the gate, the band's derivation, the row bindings
   and the exclusions — written against evidence that had not been vendored yet, so
   they failed on the missing files;
2. the evidence and the manifest landed, and those went green;
3. **then** the rule was run, once, and
   `test_the_first_application_of_the_rule_to_trex` records what it said verbatim;
4. **and only then** was anything rendered. Until that point there was no
   `out/trex_comparison_table.md`, no gap fraction asserted anywhere here, and no
   number for the rule's verdict to be argued with — which is what made running the
   rule cheap enough to do *before* deciding whether more sweep points were needed.
   A rule that has already spoken cannot be re-scoped to fit runs somebody has by
   then paid for.

Reversing 2 and 3 — reading the sweep and then writing the assertion — would produce
exactly the same green suite and would establish nothing at all. The same argument
applies to 3 and 4, which is why they were separate commits rather than one.
"""

from __future__ import annotations

import tomllib
from dataclasses import replace

import pytest

from plan1.assemble import ComparabilityError, assemble
from plan1.manifest import load_manifest, load_records
from plan1.provenance import EVIDENCE_ROOT, REPO_ROOT
from plan1.records import METRICS, Measurement

MANIFEST = REPO_ROOT / "manifests" / "trex_deformsplat.toml"
PENGUIN_MANIFEST = REPO_ROOT / "manifests" / "penguin_deformsplat.toml"

#: The step-0 fingerprint every trex row has to carry, at full precision. Fixed in
#: advance as the gate the native baseline arm had to pass, and reproduced by that
#: run exactly — so it is a pre-committed constant here rather than a number read
#: back out of the records it is supposed to be checking.
GATE_START = {
    "psnr": 18.714893341064453,
    "ssim": 0.8961969614028931,
    "lpips": 0.10315407812595367,
}
GATE_PRIMITIVES = 17779

#: The penguin's replicate band, in dB PSNR. Present so it can be asserted
#: **absent** from trex's arithmetic: a band measured on one asset selecting another
#: asset's reported row is precisely the drift that deriving it at run time exists to
#: prevent.
PENGUIN_BAND = 0.08412551879882812

#: Every row the manifest may bind at this point, and the directory each is bound
#: to. Written out rather than derived from the manifest, because the property under
#: test is that the binding is *explicit* — a check that read the manifest for both
#: halves would agree with itself no matter what the manifest said.
EXPECTED_BINDINGS = {
    "vanilla": ("null", None, "cluster/rho_probe_evidence/trex_vanilla"),
    "rho1a": ("null_replicate", 1.0, "cluster/rho_probe_evidence/trex_rho1a"),
    "rho1b": ("null_replicate", 1.0, "cluster/rho_probe_evidence/trex_rho1b"),
    "rho025": ("imposed", 0.25, "cluster/rho_probe_evidence/trex_rho025"),
    "rho4": ("imposed", 4.0, "cluster/rho_probe_evidence/trex_rho4"),
    "rho16": ("imposed", 16.0, "cluster/rho_probe_evidence/trex_rho16"),
    "baseline": ("baseline", None, "cluster/rho_probe_evidence/baseline_trex_0135_0250"),
}

if not (EVIDENCE_ROOT / "cluster" / "rho_probe_evidence" / "trex_vanilla").is_dir():
    raise FileNotFoundError(
        f"the seven trex run directories are missing under {EVIDENCE_ROOT}. This is "
        f"a bug, not a reason to skip — they are vendored here and recorded in "
        f"evidence/PROVENANCE.toml. A skip would subtract these tests from the "
        f"total and leave the summary line green, which is the failure this "
        f"repository was rebuilt to close."
    )


@pytest.fixture(scope="module")
def trex_table():
    manifest = load_manifest(MANIFEST)
    return assemble(manifest, load_records(manifest))


# ── the gate, on trex's own rows ────────────────────────────────────────────
def test_the_seven_trex_rows_pass_the_comparability_gate(trex_table):
    """All seven began from the same state, the native baseline arm included.

    That is what licenses reading the difference between them as the rigidity
    mechanism rather than as two runs that started somewhere else.
    """
    assert len(trex_table.rows) == 7
    assert trex_table.asset == "trex_0135_0250"
    assert trex_table.eval_step == 501
    assert trex_table.num_primitives == GATE_PRIMITIVES


def test_the_shared_start_is_the_triple_the_baseline_arm_was_gated_on(trex_table):
    """The gate values, read back off the assembly rather than off a plan document.

    Exact equality, not agreement to display precision: every trex row carries a
    full-precision statistics record, so there is no coarse source for the inherited
    mixed-precision rule to compare at, and relaxing to three decimals to rescue a
    near-miss is forbidden.
    """
    for metric, expected in GATE_START.items():
        assert trex_table.start[metric].value == expected
        assert trex_table.start[metric].exact


def test_the_gate_still_raises_on_a_row_that_did_not_begin_from_the_same_state():
    """The gate driven against trex's real rows, watched failing.

    A gate that has only ever been seen passing is a gate whose failure mode nobody
    knows. This perturbs one row's step-0 PSNR by a hundredth of a dB — a difference
    far too small to notice in a table and far too large to be the same checkpoint —
    and requires the assembler to refuse the whole assembly rather than warn.
    """
    manifest = load_manifest(MANIFEST)
    records = load_records(manifest)
    records["rho16"] = replace(
        records["rho16"],
        start={**records["rho16"].start, "psnr": Measurement(18.724893341064453)},
    )
    with pytest.raises(ComparabilityError, match="start"):
        assemble(manifest, records)


def test_the_gate_raises_when_a_row_arrives_from_a_different_primitive_count():
    """The second half of the fingerprint, on the same real rows.

    17,779 is the count that settled the checkpoint question — the same run's later
    checkpoint carries 33,623 — so a row arriving with a different count is the
    concrete way the wrong model gets into this table.
    """
    manifest = load_manifest(MANIFEST)
    records = load_records(manifest)
    records["baseline"] = replace(records["baseline"], num_primitives=33623)
    with pytest.raises(ComparabilityError, match="primitive count"):
        assemble(manifest, records)


# ── the band: trex's own, derived, never typed ──────────────────────────────
def test_the_band_is_derived_from_trex_own_three_replicates(trex_table):
    """The band comes off trex's null family at run time, not out of a file.

    Deriving it is what stops it drifting from the runs it describes, and the three
    runs it is derived from are named in the assembly so a reader can check which
    ones they were.
    """
    assert trex_table.band_source == ("vanilla", "rho1a", "rho1b")
    assert trex_table.band is not None
    assert trex_table.band > 0.0


def test_the_band_is_the_spread_of_the_three_replicates_it_names(trex_table):
    """Recomputed from the rows the assembly says it used.

    Not a restatement of the implementation: it reads the three PSNRs out of the
    assembled table and checks the published band is their spread, so a band that
    came from anywhere else — a constant, a different family, the wrong metric —
    fails here.
    """
    psnrs = [trex_table.row(key).metrics["psnr"].value for key in trex_table.band_source]
    assert trex_table.band == max(psnrs) - min(psnrs)


def test_the_penguin_band_is_not_substituted_for_trex(trex_table):
    """A band measured on one asset may not select another asset's reported row.

    The two assets have different geometry, different primitive counts and different
    replicate spreads; importing the penguin's figure would be the drift the
    derive-at-run-time rule exists to prevent, and it would be invisible in the
    output.
    """
    assert trex_table.band != PENGUIN_BAND


def test_no_band_is_typed_into_the_trex_manifest():
    """Asserted over the parsed keys rather than the file's prose.

    The manifest is free to *explain* the band in a comment — it should — so a text
    search would fire on the explanation. What may not exist is a key carrying a
    value, which is the only shape a typed band can take.
    """
    blob = tomllib.loads(MANIFEST.read_text())
    assert not [key for key in blob if "band" in key.lower()]
    assert not [key for row in blob["row"] for key in row if "band" in key.lower()]


# ── the rows, bound explicitly ──────────────────────────────────────────────
@pytest.mark.parametrize("key", sorted(EXPECTED_BINDINGS), ids=lambda k: k)
def test_each_row_is_bound_to_the_run_directory_it_claims(key):
    """Rows are bound explicitly, never inferred from a directory name.

    The penguin's `vanilla` and `rho1b` score within 0.0001 dB of each other, carry
    different roles, and are separable only on the secondary metrics — any heuristic
    binding would eventually swap them and produce a table wrong in a way that looks
    entirely plausible. Whether trex's replicates are that close is not assumed
    either way here; the binding is checked against a written-out expectation
    regardless.
    """
    manifest = load_manifest(MANIFEST)
    row = next(r for r in manifest.rows if r.key == key)
    role, rigidity, path = EXPECTED_BINDINGS[key]
    assert (row.role, row.rigidity, row.path) == (role, rigidity, path)
    assert row.kind == "stats_json"
    assert row.root == "archive"


def test_the_manifest_binds_these_seven_rows_and_no_others():
    manifest = load_manifest(MANIFEST)
    assert {row.key for row in manifest.rows} == set(EXPECTED_BINDINGS)


def test_the_continuation_rows_are_absent_until_the_rule_has_asked_for_them():
    """`rho32` and `rho64` are not written speculatively.

    Binding them now would encode the assumption that the sweep has not saturated —
    which is the question the rule is being run to answer. If the rule asks for them
    they are added as a manifest edit; if it does not, they never exist.
    """
    manifest = load_manifest(MANIFEST)
    assert not [row for row in manifest.rows if row.rigidity in (32.0, 64.0)]


def test_the_imposed_arm_alone_is_what_the_rule_is_fed():
    """The exclusions are as declared as the inclusions.

    The unit-rigidity replicates are not fed: they would duplicate rho = 1 in the
    sweep, and choosing between them is exactly the arbitrary decision the manifest
    exists to prevent. The mechanism-off run is not a sweep point at all — it is the
    null row and the denominator base.
    """
    manifest = load_manifest(MANIFEST)
    imposed = sorted(row.rigidity for row in manifest.rows if row.role == "imposed")
    assert imposed == [0.25, 4.0, 16.0]
    assert [row.key for row in manifest.rows if row.role == "null"] == ["vanilla"]
    assert [row.key for row in manifest.rows if row.role == "null_replicate"] == [
        "rho1a",
        "rho1b",
    ]


def test_the_two_assets_are_assembled_from_disjoint_evidence():
    """Trex rows are never added to the penguin's manifest, and the reverse.

    Stated as a property over both files rather than as an instruction in a comment:
    the gate keys on the step-0 triple, so a mixed manifest would raise — but it
    would raise *after* somebody had already merged two tables that were never
    comparable, and the useful place to catch that is here.
    """
    trex = {row["path"] for row in tomllib.loads(MANIFEST.read_text())["row"]}
    penguin = {
        row["path"] for row in tomllib.loads(PENGUIN_MANIFEST.read_text())["row"]
    }
    assert not trex & penguin
    assert all("trex" in path for path in trex)
    assert not any("trex" in path for path in penguin)


# ── every published number resolves inside this repository ──────────────────
@pytest.mark.parametrize("key", sorted(EXPECTED_BINDINGS), ids=lambda k: k)
def test_every_row_resolves_to_vendored_evidence_rather_than_a_sibling_checkout(key):
    """The property the vendoring bought, asserted for the second asset too.

    A published number may not depend on a checkout an examiner does not have. Both
    statistics files each row reads are under `evidence/`, and the resolved path is
    checked to be inside it rather than reached through a `..`.
    """
    manifest = load_manifest(MANIFEST)
    row = next(r for r in manifest.rows if r.key == key)
    run_dir = (MANIFEST.parent / manifest.roots[row.root] / row.path).resolve()
    assert run_dir.is_relative_to(EVIDENCE_ROOT)
    for name in ("val_step0000.json", f"val_step{manifest.eval_step:04d}.json"):
        assert (run_dir / "stats" / name).is_file(), name


def test_every_metric_the_rows_report_is_read_at_full_precision(trex_table):
    """No trex row is a console line, so no fraction drawn from them inherits an
    interval. The rounding-interval machinery has nothing to do here, and that is a
    property of the sources rather than a convenience."""
    for row in trex_table.rows:
        for metric in METRICS:
            assert row.metrics[metric].exact, (row.key, metric)


def test_the_wiring_limitation_owed_to_a_caption_is_stated_where_the_rows_are_bound():
    """The half of the source-hash question that did NOT come out clean, kept alive.

    The archived source snapshot hashes 6/6 to the values the pre-registration
    records, and it was taken three days *after* this sweep ran — so it brackets
    these runs rather than pinning them, and the trex consoles carry no inline
    hashes to close the gap. That is a real limitation and it is owed to any caption
    these rows are published under.

    A limitation stated only in prose is one edit from disappearing before the
    caption gets written, and this one would disappear in the flattering direction —
    "6/6 match" reads as settled if the sentence qualifying it is gone. So the
    qualification is asserted, in the file where the rows are bound.
    """
    text = MANIFEST.read_text()
    assert "OWED TO THE CAPTION" in text
    assert "BRACKETS these runs rather than pinning them" in text


def test_the_assembly_carries_the_band_assumption_wherever_the_band_is_invoked(
    trex_table,
):
    """The band is measured at unit rigidity and applied at high rigidity, which
    assumes replicate noise does not grow with the parameter. That is an assumption,
    not a measurement, and it travels with the numbers rather than being left in a
    document."""
    assert any("assumption" in note for note in trex_table.notes)


# ── the first application of the rule to trex ───────────────────────────────
#: What the pre-registered rule said the **first** time it was applied to this
#: sweep, verbatim, on 2026-08-12.
#:
#: Recording the first application — whatever it returned — was pre-committed before
#: the sweep was read, and it matters here rather than being ceremony, because of
#: which way it came out. SATURATED is the outcome that makes the two further
#: saturation runs unnecessary. It is therefore the outcome with an interested party:
#: the rule returning "no more runs needed" is exactly the verdict somebody would be
#: tempted to re-derive, re-scope, or apply a second time with a different input set
#: until it said something else. Pinning the first answer, and only the first, is
#: what makes that visible if it is ever attempted.
#:
#: The rule was run to produce this string. It was not read off the sweep and it was
#: not typed to match — see the ordering note in this module's docstring.
FIRST_VERDICT_REASON = (
    "saturated: the curve has turned over — rho=16 falls 1.5833 dB below its "
    "predecessor. Smallest rigidity within the band of the maximum (24.1106 dB "
    "at rho=4) is rho=4"
)


def test_the_first_application_of_the_rule_to_trex(trex_table):
    """The verdict, pinned. If this changes, something upstream of it changed.

    The penguin carries the mirror image of this test — its rule, applied to its
    sweep as it stood when the rule was written, returns NOT SATURATED and demands
    the two further runs. The pair is the point: the same rule, unmodified, forced
    work on one asset and forbade it on the other.
    """
    verdict = trex_table.saturation
    assert verdict.reason == FIRST_VERDICT_REASON
    assert verdict.saturated
    assert verdict.selected.key == "rho4"
    assert verdict.selected.rigidity == 4.0


def test_the_curve_turned_over_rather_than_flattening(trex_table):
    """Both readings satisfy the same predicate, and only one of them is a gain.

    `last_gain <= band` is what the rule tests, and a curve that has fallen off its
    maximum passes it just as a curve that has levelled off does. The distinction is
    invisible in the verdict's boolean and visible in its arithmetic, so it is
    asserted where it can be seen — the tail is *below* its predecessor here, not
    within a whisker above it.
    """
    verdict = trex_table.saturation
    assert verdict.last_gain is not None
    assert verdict.last_gain < 0.0
    assert "turned over" in verdict.reason


def test_the_rule_did_not_report_the_largest_swept_rigidity(trex_table):
    """Taking the smallest qualifying rigidity is what makes the rule behave here.

    ρ = 16 is the last row in the sweep and it is not the reported one: an
    over-stiffened tail can never be reported as the best setting. Only one point
    qualifies at all, so the "smallest of several" arithmetic is not what is being
    checked — what is being checked is that being *last* buys a row nothing.
    """
    verdict = trex_table.saturation
    assert [point.key for point in verdict.within_band] == ["rho4"]
    assert verdict.selected.rigidity < 16.0
    assert verdict.maximum.key == "rho4"


def test_the_verdict_calls_for_no_continuation_runs(trex_table):
    """The consequence, asserted rather than left as an inference.

    A saturated sweep asks for nothing further: no ρ = 32, no ρ = 64, and the hard
    stop at the end of the ladder is not in play because the ladder was never
    entered. Declared in advance so that an appetite for the extra runs could not
    override the rule once it had spoken — which is the direction this particular
    verdict has to be protected in.
    """
    verdict = trex_table.saturation
    assert verdict.continue_at is None
    assert not verdict.hard_stop_reached


# ── what the selected row recovers, and the bar it was judged against ───────
#: The penguin's three published fractions, as `out/comparison_table.md` prints
#: them. Present so trex's can be asserted **different** — P3 predicted that in
#: advance, and a second asset reproducing the first's percentages closely would be
#: surprising rather than reassuring.
PENGUIN_FRACTIONS = {"psnr": "63.6%", "ssim": "72.6%", "lpips": "80.4%"}

#: P1's pre-committed thresholds on the PSNR gap closed, from
#: `evidence/record/trex_comparison_prereg.md` §8. Written as the bands rather than
#: as the answer, so that the test says which branch was taken instead of merely
#: pinning a number that happens to sit in one.
P1_REPRODUCES = 0.50
P1_FAILS = 0.25


def test_the_selected_row_recovers_what_the_published_table_prints(trex_table):
    """The three fractions, at the precision the table publishes them.

    Asserted through the published table's own formatter rather than against a
    second copy of the digits, so the front page, the table and this test cannot
    come to disagree about what was recovered.
    """
    from plan1.render import format_fraction

    selected = trex_table.selected_row
    assert selected is not None and selected.fractions is not None
    published = {
        metric: format_fraction(fraction)
        for metric, fraction in selected.fractions.items()
    }
    assert published == {"psnr": "69.2%", "ssim": "69.0%", "lpips": "74.9%"}


def test_every_published_fraction_is_exact_rather_than_an_interval(trex_table):
    """No trex row is a console line, so no cell here carries a rounding interval.

    The penguin's baseline was originally a three-decimal console line and every
    fraction drawn from it printed a bracket. Trex's baseline arm was run natively
    into its own full-precision record, which is what the separate baseline-arm run
    bought, so these cells are points and `format_fraction` prints no bracket. Read
    off the output, because a bracket appearing here later would mean a row had
    been rebound to a coarser source.
    """
    selected = trex_table.selected_row
    for metric, fraction in selected.fractions.items():
        assert fraction.exact, metric
        assert fraction.low == fraction.high == fraction.value, metric


def test_P1_clears_the_bar_that_was_committed_before_the_number_was_read(trex_table):
    """The prediction, evaluated against the thresholds that were fixed in advance.

    §8 committed three branches on the PSNR gap closed — **> 50%** the penguin
    result reproduces, **25–50%** equivocal and published as equivocal, **< 25%**
    fails to reproduce — and set them relative to the penguin's 63.6% *before* any
    trex fraction had been read. Trex closes 69.2%, which is branch one.

    The bands are asserted, not just the value. A test that pinned 0.6916 alone
    would still pass if the thresholds moved underneath it, and the thresholds are
    the half that makes this a prediction rather than a measurement.
    """
    psnr = trex_table.selected_row.fractions["psnr"]
    assert psnr.value > P1_REPRODUCES, (
        f"PSNR gap closed is {psnr.value:.4f}; §8 pre-committed > {P1_REPRODUCES} "
        f"as the branch on which the penguin result reproduces"
    )
    assert P1_FAILS < P1_REPRODUCES < 1.0, "the thresholds themselves"


def test_P3_holds_the_three_fractions_differ_from_the_penguin_s(trex_table):
    """A close match would have been a reason to doubt the two tables' independence.

    §8 predicted the three would differ, and said so as a check on the apparatus
    rather than as a hope about the result: two supposedly independent comparisons
    landing on the same three percentages is the shape that means one of them is
    reading the other's numbers. They differ, and they also differ in *pattern* —
    the penguin's three ascend PSNR → SSIM → LPIPS, where trex's first two are
    within 0.2 points of each other.
    """
    from plan1.render import format_fraction

    published = {
        metric: format_fraction(fraction)
        for metric, fraction in trex_table.selected_row.fractions.items()
    }
    for metric, penguin in PENGUIN_FRACTIONS.items():
        assert published[metric] != penguin, metric


def test_the_rule_selected_a_different_rigidity_from_the_penguin_s(trex_table):
    """P2 declined to predict this, and the two assets did not agree.

    §8 refused to name an expected turnover point: ρ changes the *character* of
    trex's deformation rather than only its magnitude, so there was no ground to
    expect the penguin's ρ = 16 and predicting it would have been decoration. The
    rule selected ρ = 4. Recorded here because "the selected row is not predicted"
    is only worth stating while it is also true that the two came out different.
    """
    assert trex_table.saturation.selected.rigidity == 4.0
    assert trex_table.selected_row.label == "imposed, ρ = 4"


# ── the caption the pre-registration required ───────────────────────────────
def test_the_wiring_limitation_reaches_the_published_table_and_not_only_a_comment(
    trex_table,
):
    """§2.1 said *caption*, and a manifest comment is not a caption.

    The pre-registration declared that if the source hashes behind the pre-existing
    trex rows could not be established, "the limitation goes in the table's caption
    … rather than being glossed". They came out partial: 6/6 match, on a snapshot
    taken three days after the sweep, with no inline hashes in the consoles to close
    the gap. A reader of the table has to meet that, so it is asserted in the
    assembled notes — where the renderer prints it — rather than only in the file
    where the rows are bound.

    The word asserted is `BRACKETS`, which is the honest one. `6/6 match` reads as
    settled the moment the qualifying sentence goes missing, and it would go missing
    in the flattering direction.
    """
    wiring = [note for note in trex_table.notes if "BRACKETS" in note]
    assert len(wiring) == 1, trex_table.notes
    for owed in ("6/6", "2026-07-26", "2026-07-29", "no inline source hashes"):
        assert owed in wiring[0], owed


def test_the_penguin_declares_no_limitations_of_its_own(trex_table):
    """The manifest key is trex's, and the penguin's table is unchanged by it.

    Asserted so that "the penguin table stays byte-identical" has a reason behind
    it rather than only a diff: the mechanism that puts a caption on the second
    table is declared per manifest, and the first declares nothing.
    """
    assert load_manifest(PENGUIN_MANIFEST).limitations == ()
    assert load_manifest(MANIFEST).limitations != ()
