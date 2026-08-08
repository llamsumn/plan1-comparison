"""Tests for the readers and the precision model — below the seam.

The readers are where a source's *recorded precision* enters the system. Getting
that wrong is what lets a fraction claim a digit it does not have, so the precision
inference is tested directly rather than only through the assembler.

The one property here that is about *every* module rather than this one is at the
bottom: a record is a fact, not a variable. It is asserted in this module because
this is the module named for records, and over the whole claim surface because the
rule is the same everywhere a measured value is carried.

**The boundary assertions below were watched failing before they were kept**, against
the wrong implementation in each case — the practice `test_suite_shape.py` records
for three earlier guards. What was driven, and which test caught it:

| the source, made wrong | the test that failed |
|---|---|
| `lines[from_line : from_line + 1 + WINDOW]` → `+ WINDOW` | `test_the_primitive_count_on_the_last_line_of_the_window_is_still_found` |
| `_NUM_GS_WINDOW = 3` → `4` | `test_the_primitive_count_one_line_past_the_window_is_not_picked_up` |
| `{log_path}:{final_line + 1}` → `- 1` | `test_the_primitive_count_one_line_past_the_window_is_not_picked_up` |
| `self.decimals < 0` → `<= 0` | `test_zero_decimals_is_a_recorded_precision_and_not_an_absent_one` |
| `_coarser` returning `min(a, b)` → `max(a, b)` | `test_two_coarse_sources_are_compared_at_the_coarser_of_the_two` |
| `@dataclass(frozen=True)` → `frozen=False` on `SweepPoint` | `test_every_record_type_on_the_claim_surface_is_frozen[plan1.saturation]` |

The `_coarser` one is worth naming: it survived the whole suite before that test
existed, so "compared at the coarser of the two" — the sentence the precision model
rests on — was documented, believed, and unenforced.
"""

import dataclasses
import importlib
import json

import pytest

from plan1.records import (
    Measurement,
    read_console_log,
    read_stats_json,
)
from scripts.run_mutation import TARGETS


# ── the precision model ─────────────────────────────────────────────────────
def test_a_full_precision_measurement_has_no_interval():
    m = Measurement(25.010656356811523)
    assert m.exact
    assert m.half_ulp == 0.0
    assert m.interval == (m.value, m.value)


def test_a_recorded_precision_gives_a_half_ulp_interval():
    m = Measurement(25.055, decimals=3)
    assert not m.exact
    low, high = m.interval
    assert low == pytest.approx(25.0545)
    assert high == pytest.approx(25.0555)


def test_values_are_compared_at_the_precision_of_the_coarser_source():
    coarse = Measurement(16.764, decimals=3)
    fine = Measurement(16.76434326171875)
    assert coarse.agrees_with(fine)
    assert fine.agrees_with(coarse)


def test_disagreement_survives_the_coarser_comparison():
    assert not Measurement(16.764, decimals=3).agrees_with(Measurement(16.9))


def test_two_coarse_sources_are_compared_at_the_coarser_of_the_two():
    """The case that pins *which* precision `agrees_with` picks.

    Every other test here compares a coarse source against a full-precision one,
    where the coarser is whichever one is not `None` and the choice cannot be got
    wrong. With two recorded precisions there is a real decision, and taking the
    finer of the two would report a disagreement between sources that agree as far
    as either of them can tell — which is the whole property the precision model
    exists to defend, tested nowhere until now.
    """
    tenths = Measurement(0.5, decimals=1)
    hundredths = Measurement(0.51, decimals=2)
    assert tenths.agrees_with(hundredths)  # at one decimal, both read 0.5
    assert hundredths.agrees_with(tenths)  # and the answer is symmetric
    assert not tenths.agrees_with(Measurement(0.56, decimals=2))  # 0.6 at one place


def test_negative_decimals_are_rejected():
    with pytest.raises(ValueError, match="decimals"):
        Measurement(1.0, decimals=-1)


def test_zero_decimals_is_a_recorded_precision_and_not_an_absent_one():
    """The boundary of the `decimals >= 0` rule, on the legal side.

    Zero is where a source printed a whole number and meant it — half a unit either
    side, not full precision. `None` is the absent case and means something else
    entirely, so the two must not collapse into each other at the boundary.
    """
    m = Measurement(25.0, decimals=0)
    assert not m.exact
    assert m.half_ulp == 0.5
    assert m.interval == (24.5, 25.5)


def test_a_value_on_a_rounding_boundary_is_decided_by_round_half_even():
    """The one case the precision model calls genuinely ambiguous, pinned.

    `Measurement.agrees_with` rounds both sides to the coarser precision, and a value
    sitting exactly on a rounding boundary — 0.125 at two decimals — has no correct
    answer, only a decided one. Python rounds half to even, so it goes to 0.12 and
    agrees with 0.12 rather than with 0.13. Asserted because "no source in this study
    sits on one" is a fact about today's evidence rather than about the code, and the
    rule the code follows should be readable off a test either way.
    """
    on_the_boundary = Measurement(0.125)
    assert on_the_boundary.agrees_with(Measurement(0.12, decimals=2))
    assert not on_the_boundary.agrees_with(Measurement(0.13, decimals=2))


# ── the console reader ──────────────────────────────────────────────────────
LOG = """\
Model initialized. Number of GS: 5000
Evaluation on step=0...
 0000  "step=0 - PSNR: 16.764, SSIM: 0.9060, LPIPS: 0.102 "
Time: 0.079s/image Number of GS: 23548
 5555  "DeformSplat optimization "
Evaluation on step=501...
 0000  "step=501 - PSNR: 25.055, SSIM: 0.9535, LPIPS: 0.056 "
Time: 0.006s/image Number of GS: 23548
save checkpoint to  ./results/diva360_finetune/penguin_0217_0239/ckpt_finetune.pt
"""


@pytest.fixture
def console_log(tmp_path):
    path = tmp_path / "run.log"
    path.write_text(LOG)
    return path


def test_console_reader_infers_precision_from_the_text(console_log):
    record = read_console_log(console_log, eval_step=501, key="baseline")
    assert record.final["psnr"] == Measurement(25.055, decimals=3)
    assert record.final["ssim"] == Measurement(0.9535, decimals=4)
    assert record.final["lpips"] == Measurement(0.056, decimals=3)


def test_console_reader_takes_the_primitive_count_from_the_evaluation(console_log):
    """Not the 'Model initialized. Number of GS: 5000' line further up."""
    record = read_console_log(console_log, eval_step=501, key="baseline")
    assert record.num_primitives == 23548


def test_console_reader_records_the_line_number_as_provenance(console_log):
    record = read_console_log(console_log, eval_step=501, key="baseline")
    assert f"{console_log}:7" in record.provenance  # the step=501 line
    assert f"{console_log}:3" in record.provenance  # the step=0 line


def test_console_reader_parses_the_checkpoint_as_provenance_only(console_log):
    record = read_console_log(console_log, eval_step=501, key="baseline")
    assert record.checkpoint.endswith("ckpt_finetune.pt")


def test_console_reader_raises_on_a_missing_step(console_log):
    with pytest.raises(ValueError, match="no step-999 evaluation"):
        read_console_log(console_log, eval_step=999, key="baseline")


def test_console_reader_raises_on_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such console log"):
        read_console_log(tmp_path / "absent.log", eval_step=501, key="baseline")


# ── the search window for the primitive count, at both its edges ────────────
# The count is printed on the line after the evaluation in every archived log, and
# the window is small on purpose: it keeps an unrelated later "Number of GS" from
# being picked up as this evaluation's. That makes its size a decision, and the
# arithmetic implementing it — `lines[from_line : from_line + 1 + WINDOW]` — was
# assertable only in the middle, where an off-by-one changes nothing. Both edges are
# driven here, so widening or narrowing the window by a line fails.
def write_log_with_the_count(tmp_path, offset):
    """A log whose primitive count sits `offset` lines after the step-501 line."""
    lines = [
        ' 0000  "step=0 - PSNR: 16.764, SSIM: 0.9060, LPIPS: 0.102 "',
        ' 0000  "step=501 - PSNR: 25.055, SSIM: 0.9535, LPIPS: 0.056 "',
        *["Time: 0.006s/image"] * (offset - 1),
        "Time: 0.006s/image Number of GS: 23548",
    ]
    path = tmp_path / f"count_at_offset_{offset}.log"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_the_primitive_count_on_the_last_line_of_the_window_is_still_found(tmp_path):
    """Three lines below the evaluation — the furthest the window reaches."""
    record = read_console_log(
        write_log_with_the_count(tmp_path, 3), eval_step=501, key="baseline"
    )
    assert record.num_primitives == 23548


def test_the_primitive_count_one_line_past_the_window_is_not_picked_up(tmp_path):
    """Four lines below, and the reader refuses rather than reaching further.

    Refusing is the right answer and not a limitation: a count that far from its
    evaluation is not demonstrably that evaluation's, and a reader that stretched to
    find one would silently attribute another run's primitive count to this row —
    which the comparability gate would then compare against, and pass.

    The refusal also has to say *where*, in the file's own 1-based numbering, so the
    message can be pasted into an editor. That arithmetic is asserted here rather
    than left as the only untested `+ 1` in the reader.
    """
    log = write_log_with_the_count(tmp_path, 4)
    with pytest.raises(ValueError, match="no primitive count within 3 lines") as raised:
        read_console_log(log, eval_step=501, key="baseline")
    # the step-501 line is the file's second line, so the message must say `:2`
    assert f"{log}:2" in str(raised.value)


# ── the stats-json reader ───────────────────────────────────────────────────
def write_run(tmp_path, *, start, final, num_gs=23548, step=501):
    stats = tmp_path / "stats"
    stats.mkdir(parents=True, exist_ok=True)
    (stats / "val_step0000.json").write_text(json.dumps({**start, "num_GS": num_gs}))
    (stats / f"val_step{step:04d}.json").write_text(json.dumps({**final, "num_GS": num_gs}))
    return tmp_path


def test_stats_reader_keeps_full_precision(tmp_path):
    run = write_run(
        tmp_path / "run",
        start={"psnr": 16.76434326171875, "ssim": 0.906018853187561, "lpips": 0.1019977554678917},
        final={"psnr": 22.953351974487305, "ssim": 0.9442539215087891, "lpips": 0.06339161843061447},
    )
    record = read_stats_json(run, eval_step=501, key="rho16")
    assert record.final["psnr"].exact
    assert record.final["psnr"].value == 22.953351974487305
    assert record.num_primitives == 23548


def test_stats_reader_raises_on_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such statistics file"):
        read_stats_json(tmp_path / "absent", eval_step=501, key="rho16")


def test_stats_reader_raises_when_the_primitive_count_moved_mid_run(tmp_path):
    run = tmp_path / "run"
    stats = run / "stats"
    stats.mkdir(parents=True)
    triple = {"psnr": 1.0, "ssim": 0.9, "lpips": 0.1}
    (stats / "val_step0000.json").write_text(json.dumps({**triple, "num_GS": 23548}))
    (stats / "val_step0501.json").write_text(json.dumps({**triple, "num_GS": 23549}))
    with pytest.raises(ValueError, match="primitive count moved"):
        read_stats_json(run, eval_step=501, key="rho16")


def test_stats_reader_raises_on_missing_metric_keys(tmp_path):
    run = tmp_path / "run"
    stats = run / "stats"
    stats.mkdir(parents=True)
    (stats / "val_step0000.json").write_text(json.dumps({"psnr": 1.0, "num_GS": 1}))
    (stats / "val_step0501.json").write_text(json.dumps({"psnr": 1.0, "num_GS": 1}))
    with pytest.raises(ValueError, match="missing keys"):
        read_stats_json(run, eval_step=501, key="rho16")


# ── a record is a fact, not a variable ──────────────────────────────────────
#: Every module a published number passes through, **derived** from the set the
#: mutation run measures rather than restated beside it. Two hand-kept copies of one
#: list is the drift `audit.py` was built to end: add a module to one and this
#: property silently stops covering it, with nothing failing to say so.
CLAIM_SURFACE = tuple(
    target.removesuffix(".py").replace("/", ".") for target in TARGETS
)


def record_types(module_name):
    """The dataclasses a module declares itself, ignoring any it imported."""
    module = importlib.import_module(module_name)
    return [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type)
        and dataclasses.is_dataclass(obj)
        and obj.__module__ == module_name
    ]


@pytest.mark.parametrize("module_name", CLAIM_SURFACE)
def test_every_record_type_on_the_claim_surface_is_frozen(module_name):
    """`frozen=True` on all fourteen of them, asserted rather than assumed.

    Mutation found this: every one could be flipped to `frozen=False` and nothing
    failed, which made the strongest-looking property in the data layer also the
    least defended. It is not decoration. The comparability gate validates a set of
    records and then hands them to the assembler; if a record could be rewritten
    afterwards, what the table reports and what the gate approved would be two
    different things, and nothing would say so.

    Asserted by walking the module rather than by listing the classes, so a new
    record type is covered the moment it is written instead of the moment someone
    remembers to add it here.
    """
    mutable = [
        obj.__name__
        for obj in record_types(module_name)
        if not obj.__dataclass_params__.frozen
    ]
    assert not mutable, (
        f"{module_name} carries record types that can be rewritten after they are "
        f"validated: {mutable}"
    )


def test_the_claim_surface_declares_record_types_at_all():
    """The non-vacuity guard, held once over the whole surface rather than per module.

    Per module it would be wrong: `box_b/edge_weights.py` is two functions and no
    dataclass, and demanding one there would be demanding a design it does not have.
    Held collectively it says the thing that matters — that the test above has
    fourteen real classes to be right about, and is not passing because it found
    nothing to look at.
    """
    found = {
        obj.__name__ for name in CLAIM_SURFACE for obj in record_types(name)
    }
    assert len(found) >= 14, sorted(found)
