"""assemble.py — **the seam**.

A pure function from a declared manifest plus the run records to a validated
comparison table. Comparability gating and gap arithmetic both sit behind it, so a
fixture can drive every failure mode without a GPU, an asset file, or a network.
This is the highest available seam: everything above it is presentation, everything
below it is file reading.

The assembler refuses to emit a table unless every row demonstrably began from the
same state. Failure raises; it does not warn. Prior experience on this project is
that a silently-wrong comparison produces plausible numbers, which is the worst
outcome available.

Rules implemented here are declared in
``all_record/deformsplat_corroboration/plan1_prereg.md`` and must not be changed
without recording a deviation there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan1.manifest import ROLES, Manifest, ManifestRow
from plan1.records import METRICS, Measurement, RunRecord
from plan1.saturation import SaturationVerdict, SweepPoint, select_saturated_row

#: Stated wherever the band is invoked. The band was measured at unit rigidity;
#: applying it at high rigidity assumes replicate noise does not grow with the
#: parameter. That is an assumption, not a measurement (plan1_prereg.md §2).
BAND_ASSUMPTION = (
    "The replicate band was measured at unit rigidity. Applying it across the sweep "
    "assumes replicate noise does not grow with rigidity; this is an assumption, "
    "not a measurement."
)

NULL_EQUIVALENCE = (
    "The no-rigidity row is the mechanism-off run alone. Its equivalence to the "
    "unit-rigidity runs rests on code inspection — the scaling helper early-returns "
    "its input at unit rigidity — and not on measurement: the gate that would have "
    "established it end to end is the one that failed."
)


class AssemblyError(Exception):
    """Base for every refusal to emit a table."""


class ManifestError(AssemblyError):
    """The manifest is not a well-formed description of a comparison."""


class ComparabilityError(AssemblyError):
    """The rows do not demonstrably begin from the same state."""


@dataclass(frozen=True)
class GapFraction:
    """How much of the null→baseline interval a row covers, on one metric.

    Computed identically for all three metrics as ``(row - null) / (baseline -
    null)``. The sign of LPIPS needs no special case: inverting the metric flips
    numerator and denominator together, so "more is better" already holds
    uniformly and no reader has to invert a column mentally.

    ``low``/``high`` bound the fraction over the rounding intervals of its inputs.
    They collapse onto ``value`` when every input was recorded at full precision.
    """

    value: float
    low: float
    high: float
    exact: bool

    @property
    def spread(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class TableRow:
    key: str
    label: str
    role: str
    rigidity: float | None
    information: str
    metrics: Mapping[str, Measurement]
    provenance: str
    fractions: Mapping[str, GapFraction] | None = None


@dataclass(frozen=True)
class ComparisonTable:
    asset: str
    manifest_source: str
    eval_step: int
    num_primitives: int
    #: The shared starting values, printed so a reader can verify at a glance that
    #: all arms began from the same state.
    start: Mapping[str, Measurement]
    rows: tuple[TableRow, ...]
    band: float | None
    band_source: tuple[str, ...]
    saturation: SaturationVerdict | None
    notes: tuple[str, ...]

    def row(self, key: str) -> TableRow:
        for row in self.rows:
            if row.key == key:
                return row
        raise KeyError(key)

    @property
    def selected_row(self) -> TableRow | None:
        """The row the pre-registered saturation rule selects, or ``None``.

        ``None`` whenever the curve has not saturated — an unsaturated sweep yields
        no reportable row, by declaration.
        """
        if self.saturation is None or self.saturation.selected is None:
            return None
        return self.row(self.saturation.selected.key)


def assemble(manifest: Manifest, records: Mapping[str, RunRecord]) -> ComparisonTable:
    """Validate the rows and assemble the comparison table.

    Raises
    ------
    ManifestError
        The manifest names a record that was not supplied, carries an unknown role,
        or does not describe both endpoints the gap fraction is measured between.
    ComparabilityError
        Two rows disagree on their evaluation step, primitive count, or step-0
        fingerprint — so a difference between them is not attributable to the
        rigidity mechanism.
    """
    rows = manifest.rows
    _check_manifest(rows, records)
    ordered = [(row, records[row.key]) for row in rows]
    _check_comparable(manifest, ordered)

    baseline = records[_only(rows, "baseline").key]
    null = records[_only(rows, "null").key]

    table_rows = tuple(
        TableRow(
            key=row.key,
            label=row.label,
            role=row.role,
            rigidity=row.rigidity,
            information=row.information,
            metrics=record.final,
            provenance=record.provenance,
            fractions=(
                {
                    metric: _gap_fraction(
                        null.final[metric], record.final[metric], baseline.final[metric]
                    )
                    for metric in METRICS
                }
                if row.role == "imposed"
                else None
            ),
        )
        for row, record in ordered
    )

    band, band_source, notes = _derive_band(rows, records)
    saturation = _saturation(rows, records, band)

    first = ordered[0][1]
    return ComparisonTable(
        asset=manifest.asset,
        manifest_source=manifest.source,
        eval_step=manifest.eval_step,
        num_primitives=first.num_primitives,
        start=first.start,
        rows=table_rows,
        band=band,
        band_source=band_source,
        saturation=saturation,
        notes=tuple(notes),
    )


# ── validation ──────────────────────────────────────────────────────────────
def _check_manifest(
    rows: Sequence[ManifestRow], records: Mapping[str, RunRecord]
) -> None:
    if not rows:
        raise ManifestError("the manifest declares no rows")

    for row in rows:
        if row.role not in ROLES:
            raise ManifestError(
                f"row {row.key!r}: unknown role {row.role!r}; expected one of "
                f"{list(ROLES)}"
            )
        if row.key not in records:
            raise ManifestError(
                f"the manifest names record {row.key!r}, which was not supplied"
            )
        if row.role == "imposed" and row.rigidity is None:
            raise ManifestError(
                f"row {row.key!r} is an imposed-rigidity row but declares no rigidity"
            )

    for role in ("baseline", "null"):
        found = [row for row in rows if row.role == role]
        if len(found) != 1:
            raise ManifestError(
                f"the gap fraction needs exactly one {role!r} row; the manifest "
                f"declares {len(found)} ({[r.key for r in found]})"
            )


def _check_comparable(
    manifest: Manifest, ordered: Sequence[tuple[ManifestRow, RunRecord]]
) -> None:
    """The gate. Every row must demonstrably have begun from the same state.

    The step-0 metric triple is the fingerprint, deliberately, rather than a
    recorded checkpoint identifier: a path is a string that may have been
    overwritten between runs, whereas a matching step-0 evaluation is content-level
    evidence that the same weights were scored by the same camera on the same data.

    Rows are compared **pairwise**, not each against the first row. Comparing at
    the coarser of two precisions is not transitive — two full-precision rows that
    differ in the fourth decimal both agree with a three-decimal console line — so
    anchoring on one row would make the gate's strictness depend on manifest order.
    """
    for row, record in ordered:
        if record.eval_step != manifest.eval_step:
            raise ComparabilityError(
                f"row {row.key!r} disagrees on the evaluation step: manifest "
                f"declares {manifest.eval_step}, record was evaluated at "
                f"{record.eval_step}"
            )

    for index, (row, record) in enumerate(ordered):
        for other_row, other in ordered[index + 1 :]:
            if record.num_primitives != other.num_primitives:
                raise ComparabilityError(
                    f"rows {row.key!r} and {other_row.key!r} disagree on the "
                    f"primitive count: {record.num_primitives} against "
                    f"{other.num_primitives}"
                )

    for index, (row, record) in enumerate(ordered):
        for other_row, other in ordered[index + 1 :]:
            for metric in METRICS:
                mine, theirs = record.start[metric], other.start[metric]
                if not mine.agrees_with(theirs):
                    raise ComparabilityError(
                        f"rows {row.key!r} and {other_row.key!r} disagree on the "
                        f"step-0 start fingerprint: {metric} {mine.value!r} against "
                        f"{theirs.value!r} — the rows did not begin from the same "
                        f"state, so the difference between them is not attributable "
                        f"to the rigidity mechanism"
                    )


# ── arithmetic ──────────────────────────────────────────────────────────────
def _gap_fraction(
    null: Measurement, row: Measurement, baseline: Measurement
) -> GapFraction:
    denominator = baseline.value - null.value
    if denominator == 0.0:
        raise AssemblyError(
            "the baseline and the null row score identically, so there is no gap "
            "to express a fraction of"
        )
    value = (row.value - null.value) / denominator

    # Bound the fraction over the corners of the inputs' rounding intervals. The
    # fraction is monotone in each input separately across the intervals in play
    # (the denominator is nowhere near zero), so the extremes sit at the corners.
    corners = [
        (r - n) / (b - n)
        for n in null.interval
        for r in row.interval
        for b in baseline.interval
        if (b - n) != 0.0
    ]
    if not corners:
        raise AssemblyError(
            "the baseline and the null row overlap across their whole rounding "
            "intervals, so no gap fraction is defined"
        )
    return GapFraction(
        value=value,
        low=min(corners),
        high=max(corners),
        exact=null.exact and row.exact and baseline.exact,
    )


def _derive_band(
    rows: Sequence[ManifestRow], records: Mapping[str, RunRecord]
) -> tuple[float | None, tuple[str, ...], list[str]]:
    """The replicate band, derived from the null family rather than typed in.

    Deriving it at run time is what stops it drifting from the runs it describes.
    """
    family = [row.key for row in rows if row.role in ("null", "null_replicate")]
    notes = [NULL_EQUIVALENCE]

    if len(family) < 2:
        notes.append(
            "No replicate band: fewer than two null-family runs were declared, so "
            "the saturation rule cannot be applied."
        )
        return None, (), notes

    psnrs = [records[key].final["psnr"].value for key in family]
    notes.append(BAND_ASSUMPTION)
    return max(psnrs) - min(psnrs), tuple(family), notes


def _saturation(
    rows: Sequence[ManifestRow],
    records: Mapping[str, RunRecord],
    band: float | None,
) -> SaturationVerdict | None:
    if band is None:
        return None
    sweep = [
        SweepPoint(
            rigidity=row.rigidity,  # type: ignore[arg-type]  # validated above
            psnr=records[row.key].final["psnr"].value,
            key=row.key,
        )
        for row in rows
        if row.role == "imposed"
    ]
    if not sweep:
        return None
    return select_saturated_row(sweep, band=band)


def _only(rows: Sequence[ManifestRow], role: str) -> ManifestRow:
    return next(row for row in rows if row.role == role)
