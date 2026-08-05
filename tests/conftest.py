"""Fixture builders for the assembler suite.

Everything here constructs records in memory. The assembler is a pure function, so
its whole failure surface is drivable without a GPU, an asset file, or a network —
which is the point of putting the seam where it is.
"""

import sys
from pathlib import Path

import pytest

from plan1.manifest import Manifest, ManifestRow
from plan1.records import Measurement, RunRecord

#: The method repository, consumed by the conformance test as the reference rule.
#: An editable install (``pip install -e ../arap-deform-3dgs``) is the documented
#: path; this fallback keeps the suite runnable in a bare checkout. Either way the
#: binding is live — it resolves to the sibling working tree, not to a copy.
METHOD_REPO = Path(__file__).resolve().parents[2] / "arap-deform-3dgs"
if METHOD_REPO.is_dir() and str(METHOD_REPO) not in sys.path:
    sys.path.insert(0, str(METHOD_REPO))


#: The archived step-0 fingerprint, at full precision, shared by every penguin run.
START = {
    "psnr": 16.76434326171875,
    "ssim": 0.906018853187561,
    "lpips": 0.1019977554678917,
}


def exact(mapping):
    return {k: Measurement(v) for k, v in mapping.items()}


def rounded(mapping, decimals):
    """A triple as a console line records it — value plus its recorded precision."""
    return {
        k: Measurement(round(v, decimals[k]), decimals=decimals[k])
        for k, v in mapping.items()
    }


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
        asset=asset, eval_step=eval_step, rows=tuple(rows), source="fixture://manifest"
    )


@pytest.fixture
def three_row_case():
    """The minimal complete comparison: null, imposed, baseline.

    Values are the archived penguin numbers so the fixture doubles as a check that
    the arithmetic matches the published table.
    """
    rows = [
        make_row("null", "null", label="none (grouping off, unit rigidity)"),
        make_row("imposed16", "imposed", rigidity=16, information="static asset + one handle"),
        make_row("baseline", "baseline", information="observed before/after motion"),
    ]
    records = {
        "null": make_record("null", 19.277395248413086, 0.9198831915855408, 0.09161172062158585),
        "imposed16": make_record(
            "imposed16", 22.953351974487305, 0.9442539215087891, 0.06339161843061447
        ),
        "baseline": make_record("baseline", 25.055, 0.9535, 0.056),
    }
    return make_manifest(rows), records
