"""Fixture builders for the assembler suite.

Everything here constructs records in memory. The assembler is a pure function, so
its whole failure surface is drivable without a GPU, an asset file, or a network —
which is the point of putting the seam where it is.
"""

import pytest

from plan1.manifest import Manifest, ManifestRow
from plan1.records import Measurement, RunRecord

# This file used to inject a sibling working tree onto `sys.path` so the
# conformance test could import the reference rule. That injection is the
# reason the suite reported a different number depending on what else happened to
# be checked out beside it. The port brought the rule in; `box_b` is now a package in this
# repository and is imported like any other. Nothing here touches `sys.path`.

#: The archived step-0 fingerprint, at full precision, shared by every penguin run.
START = {
    "psnr": 16.76434326171875,
    "ssim": 0.906018853187561,
    "lpips": 0.1019977554678917,
}

#: The precision the 2026-07-22 console line recorded the baseline at.
CONSOLE_DECIMALS = {"psnr": 3, "ssim": 4, "lpips": 3}

#: The parent spec's published gap-recovered cells, exactly as it printed them: one
#: decimal place, as percentages. Each therefore *denotes an interval* of its own —
#: 63.6% asserts only that the value lies in [63.55%, 63.65%]. Treating one of these
#: as an exact number is the mistake the assembly spec's retraction records, so they
#: are carried here as Measurements and never as bare floats.
PARENT_CELLS = {
    "psnr": Measurement(0.636, decimals=3),
    "ssim": Measurement(0.726, decimals=3),
    "lpips": Measurement(0.792, decimals=3),
}


def overlaps(fraction, cell):
    """Does the assembler's interval overlap a published cell's interval?

    The pre-registered comparability rule — mixed precision compares at the coarser
    precision — applied to a published cell rather than to a run record.

    **Not for the full-precision fixture.** An exact fraction has a zero-width
    interval, so this collapses back into the point-in-interval comparison being
    retracted — and the LPIPS cell legitimately leaves the parent's interval there,
    because the input sharpened. See
    ``test_the_full_precision_lpips_cell_legitimately_leaves_the_parent_interval``.
    """
    low, high = cell.interval
    return fraction.low <= high and fraction.high >= low


def make_record(
    key,
    psnr,
    ssim,
    lpips,
    *,
    start=None,
    num_primitives=23548,
    eval_step=501,
    decimals=None,
):
    """One run record. ``decimals`` maps a metric to its recorded precision."""
    decimals = decimals or {}
    final = {
        k: Measurement(round(v, decimals[k]), decimals=decimals[k])
        if k in decimals
        else Measurement(v)
        for k, v in (("psnr", psnr), ("ssim", ssim), ("lpips", lpips))
    }
    start_values = START if start is None else start
    start_triple = {
        k: Measurement(round(v, decimals[k]), decimals=decimals[k])
        if k in decimals
        else Measurement(v)
        for k, v in start_values.items()
    }
    return RunRecord(
        key=key,
        start=start_triple,
        final=final,
        num_primitives=num_primitives,
        eval_step=eval_step,
        source=f"fixture://{key}",
        provenance=f"fixture record {key}",
    )


def make_row(key, role, *, rigidity=None, label=None, information="—"):
    return ManifestRow(
        key=key,
        label=label or key,
        role=role,
        rigidity=rigidity,
        information=information,
        kind="stats_json",
        root="fixture",
        path=key,
    )


def make_manifest(rows, *, asset="penguin_0217_0239", eval_step=501):
    return Manifest(
        asset=asset,
        eval_step=eval_step,
        rows=tuple(rows),
        source="fixture://manifest",
        assembled="2026-08-06",
    )


def _three_rows():
    return [
        make_row("null", "null", label="none (grouping off, unit rigidity)"),
        make_row("imposed16", "imposed", rigidity=16, information="static asset + one handle"),
        make_row("baseline", "baseline", information="observed before/after motion"),
    ]


def _null_and_imposed():
    return {
        "null": make_record("null", 19.277395248413086, 0.9198831915855408, 0.09161172062158585),
        "imposed16": make_record(
            "imposed16", 22.953351974487305, 0.9442539215087891, 0.06339161843061447
        ),
    }


@pytest.fixture
def three_row_case():
    """The minimal complete comparison as the CONSOLE-BASELINE world recorded it.

    This is the branch plan1_prereg.md §7 declared as its fallback and did not take:
    the baseline known only from the 2026-07-22 console line, at 3 / 4 / 3 decimals.
    It is kept as a live fixture because the branch was declared, and because the
    interval arithmetic only has anything to do when a source is coarse.

    The recorded precision is what stops these intervals collapsing to zero width.
    That collapse is what made a point estimate with roughly two tenths of a
    percentage point of slack look like a hard fact — see the retraction in
    `docs/specs/plan-1-comparison-assembly-spec.md`.
    """
    records = _null_and_imposed()
    records["baseline"] = make_record(
        "baseline", 25.055, 0.9535, 0.056, decimals=CONSOLE_DECIMALS
    )
    return make_manifest(_three_rows()), records


@pytest.fixture
def three_row_case_full_precision():
    """The same comparison as the CURRENT manifest publishes it.

    Preflight recovered the baseline run's own statistics record, so every input is
    a full-precision float and every fraction is exact. This mirrors the path every
    published number now travels.
    """
    records = _null_and_imposed()
    records["baseline"] = make_record(
        "baseline", 25.054527282714844, 0.9534690976142883, 0.05649951100349426
    )
    return make_manifest(_three_rows()), records
