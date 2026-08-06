"""records.py — run records and the readers that produce them.

This sits **below** the assembler seam: everything here is file reading. Two source
kinds exist, and they differ in one way that matters to the gate — the precision at
which they recorded their numbers.

* ``stats_json`` — a run directory's ``stats/val_step*.json``, full float precision.
* ``console_log`` — a line of training console output, at display precision. The
  baseline row is one of these (the 2026-07-22 spike), and its precision is what
  every headline fraction inherits.

Precision is **inferred from the source text**, never declared in the manifest: the
number of digits after the decimal point in ``PSNR: 25.055`` is what the log
actually claims, so reading it off the text is the only way the two cannot drift
apart.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from plan1.provenance import display_path

#: The three reported metrics. LPIPS is inverted — lower is better.
METRICS: tuple[str, ...] = ("psnr", "ssim", "lpips")

#: ``True`` where a larger value is a better one.
HIGHER_IS_BETTER: Mapping[str, bool] = {"psnr": True, "ssim": True, "lpips": False}


@dataclass(frozen=True)
class Measurement:
    """A recorded number, together with the precision it was recorded at.

    ``decimals is None`` means the source held full float precision. Otherwise the
    source printed the value to ``decimals`` places, and the true value lies
    somewhere in ``interval`` — a half-ulp either side.

    Two values recorded at different precisions are compared at the coarser of the
    two, by rounding both. (A value sitting exactly on a rounding boundary is
    genuinely ambiguous at that precision; Python's round-half-even decides it, and
    no source in this study sits on one.)
    """

    value: float
    decimals: int | None = None

    def __post_init__(self) -> None:
        if self.decimals is not None and self.decimals < 0:
            raise ValueError(f"decimals must be >= 0; got {self.decimals}")

    @property
    def exact(self) -> bool:
        return self.decimals is None

    @property
    def half_ulp(self) -> float:
        """Half the last recorded place — zero for a full-precision value."""
        return 0.0 if self.decimals is None else 0.5 * 10.0 ** (-self.decimals)

    @property
    def interval(self) -> tuple[float, float]:
        h = self.half_ulp
        return (self.value - h, self.value + h)

    def at(self, decimals: int | None) -> float:
        """This value rounded to ``decimals`` places (``None`` = leave it alone)."""
        return self.value if decimals is None else round(self.value, decimals)

    def agrees_with(self, other: "Measurement") -> bool:
        """Do the two agree at the precision of the coarser source?"""
        coarser = _coarser(self.decimals, other.decimals)
        return self.at(coarser) == other.at(coarser)


def _coarser(a: int | None, b: int | None) -> int | None:
    """The coarser of two precisions. ``None`` (full precision) is the finer one."""
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


@dataclass(frozen=True)
class RunRecord:
    """One evaluated run: where it started, where it finished, and where it came from."""

    key: str
    start: Mapping[str, Measurement]  # the step-0 triple — the comparability fingerprint
    final: Mapping[str, Measurement]  # the triple at the evaluation step
    num_primitives: int
    eval_step: int
    source: str
    provenance: str
    #: Parsed where a source carries it. Provenance only — the gate never rests on
    #: a path, because a path is a string that may have been overwritten.
    checkpoint: str | None = None

    def __post_init__(self) -> None:
        for name, triple in (("start", self.start), ("final", self.final)):
            missing = set(METRICS) - set(triple)
            if missing:
                raise ValueError(
                    f"record {self.key!r} {name} triple is missing {sorted(missing)}"
                )


# ── readers ─────────────────────────────────────────────────────────────────
def read_stats_json(run_dir: Path, eval_step: int, key: str) -> RunRecord:
    """Read a run directory's ``stats/val_step0000.json`` + ``val_step{step}.json``."""
    run_dir = Path(run_dir)
    start_path = run_dir / "stats" / "val_step0000.json"
    final_path = run_dir / "stats" / f"val_step{eval_step:04d}.json"
    for path in (start_path, final_path):
        if not path.is_file():
            raise FileNotFoundError(f"record {key!r}: no such statistics file: {path}")

    start = json.loads(start_path.read_text())
    final = json.loads(final_path.read_text())
    _require_keys(start, start_path)
    _require_keys(final, final_path)

    if start["num_GS"] != final["num_GS"]:
        raise ValueError(
            f"record {key!r}: primitive count moved between step 0 and step "
            f"{eval_step} ({start['num_GS']} -> {final['num_GS']})"
        )

    return RunRecord(
        key=key,
        start={m: Measurement(float(start[m])) for m in METRICS},
        final={m: Measurement(float(final[m])) for m in METRICS},
        num_primitives=int(final["num_GS"]),
        eval_step=eval_step,
        source=display_path(run_dir),
        provenance=(
            f"{key}: {display_path(final_path)} (step {eval_step}), "
            f"start {display_path(start_path)}"
        ),
    )


def _require_keys(blob: dict, path: Path) -> None:
    missing = ({*METRICS, "num_GS"}) - set(blob)
    if missing:
        raise ValueError(f"{path}: missing keys {sorted(missing)}")


#: ``step=501 - PSNR: 25.055, SSIM: 0.9535, LPIPS: 0.056``
_EVAL_LINE = re.compile(
    r"step=(?P<step>\d+)\s*-\s*"
    r"PSNR:\s*(?P<psnr>[-\d.]+)\s*,\s*"
    r"SSIM:\s*(?P<ssim>[-\d.]+)\s*,\s*"
    r"LPIPS:\s*(?P<lpips>[-\d.]+)"
)
_NUM_GS = re.compile(r"Number of GS:\s*(\d+)")
_CKPT = re.compile(r"save checkpoint to\s+(?P<path>\S+)")

#: How far past an evaluation line to look for its primitive count. The count is
#: printed on the line immediately after in every archived log; the small window
#: keeps an unrelated later "Number of GS" from being picked up.
_NUM_GS_WINDOW = 3


def read_console_log(log_path: Path, eval_step: int, key: str) -> RunRecord:
    """Parse a training console log's step-0 and evaluation-step lines.

    Precision comes from the text: ``25.055`` is recorded as three decimals, and
    every fraction derived from it carries the resulting interval.
    """
    log_path = Path(log_path)
    if not log_path.is_file():
        raise FileNotFoundError(f"record {key!r}: no such console log: {log_path}")
    lines = log_path.read_text(errors="replace").splitlines()

    start, start_line = _find_eval(lines, 0, log_path, key)
    final, final_line = _find_eval(lines, eval_step, log_path, key)

    num_gs = _find_num_gs(lines, final_line)
    if num_gs is None:
        raise ValueError(
            f"record {key!r}: no primitive count within {_NUM_GS_WINDOW} lines of "
            f"the step-{eval_step} evaluation at {log_path}:{final_line + 1}"
        )

    checkpoint = None
    for line in lines[final_line:]:
        found = _CKPT.search(line)
        if found:
            checkpoint = found.group("path")
            break

    return RunRecord(
        key=key,
        start=start,
        final=final,
        num_primitives=num_gs,
        eval_step=eval_step,
        source=display_path(log_path),
        provenance=(
            f"{key}: {display_path(log_path)}:{final_line + 1} (step {eval_step}), "
            f"start {display_path(log_path)}:{start_line + 1}"
        ),
        checkpoint=checkpoint,
    )


def _find_eval(
    lines: list[str], step: int, path: Path, key: str
) -> tuple[dict[str, Measurement], int]:
    for index, line in enumerate(lines):
        found = _EVAL_LINE.search(line)
        if found and int(found.group("step")) == step:
            return (
                {m: _measure_text(found.group(m)) for m in METRICS},
                index,
            )
    raise ValueError(f"record {key!r}: no step-{step} evaluation line in {path}")


def _find_num_gs(lines: list[str], from_line: int) -> int | None:
    for line in lines[from_line : from_line + 1 + _NUM_GS_WINDOW]:
        found = _NUM_GS.search(line)
        if found:
            return int(found.group(1))
    return None


def _measure_text(text: str) -> Measurement:
    """A number as the log printed it, with the precision the text claims."""
    _, _, fraction = text.partition(".")
    return Measurement(float(text), decimals=len(fraction))
