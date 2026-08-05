"""Tests for the readers and the precision model — below the seam.

The readers are where a source's *recorded precision* enters the system. Getting
that wrong is what lets a fraction claim a digit it does not have, so the precision
inference is tested directly rather than only through the assembler.
"""

import json

import pytest

from plan1.records import (
    Measurement,
    read_console_log,
    read_stats_json,
)


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


def test_negative_decimals_are_rejected():
    with pytest.raises(ValueError, match="decimals"):
        Measurement(1.0, decimals=-1)


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
