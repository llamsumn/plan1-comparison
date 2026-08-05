"""saturation.py — the pre-registered rule that selects the reported rigidity.

Declared in `all_record/deformsplat_corroboration/plan1_prereg.md` §3, before any
run, so that the choice of reported row is made by a criterion rather than by eye
once the numbers arrive:

    The reported imposed-rigidity setting is the SMALLEST rigidity value whose PSNR
    falls within the replicate band of the sweep maximum.

    If the largest swept rigidity is still gaining more than the band over its
    predecessor, the curve has not saturated: no row is reported and the sweep
    continues by the next declared step.

PSNR is the sole selector because the replicate band is measured in dB and exists
only for that metric; SSIM and LPIPS are reported *at the selected row* rather than
each nominating its own. Taking the smallest qualifying rigidity rather than the
argmax is what makes the rule behave when the curve turns over — an over-stiffened
tail can never be reported as the best setting.

Pure, deterministic, CPU-only. The band is passed in rather than baked in; the
assembler derives it from the null replicates so it cannot drift from the runs it
describes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

#: The continuation ladder, declared in plan1_prereg.md §3.1. The sweep does not
#: continue past the final entry under any reading of the numbers.
CONTINUATION_STEPS: tuple[float, ...] = (32.0, 64.0, 128.0, 256.0)


@dataclass(frozen=True)
class SweepPoint:
    """One swept rigidity and the PSNR it scored."""

    rigidity: float
    psnr: float
    key: str = ""  # manifest key, carried through for provenance


@dataclass(frozen=True)
class SaturationVerdict:
    """What the rule decided, and the arithmetic it decided it on."""

    saturated: bool
    selected: SweepPoint | None
    maximum: SweepPoint
    band: float
    last_gain: float | None
    continue_at: float | None
    hard_stop_reached: bool
    reason: str
    #: Every point the rule considered qualifying, smallest rigidity first.
    #: Empty whenever the curve has not saturated.
    within_band: tuple[SweepPoint, ...] = ()


def select_saturated_row(
    sweep: Sequence[SweepPoint],
    band: float,
    continuation_steps: Sequence[float] = CONTINUATION_STEPS,
) -> SaturationVerdict:
    """Apply the pre-registered saturation rule to a sweep.

    Parameters
    ----------
    sweep :
        The swept points. Order is irrelevant; rigidity values must be distinct.
    band :
        The replicate band, in dB PSNR. Derived from the null replicates, not typed.
    continuation_steps :
        The declared ladder of further rigidity values. The last entry is a hard
        stop: reaching it without saturating is reported as the finding.

    Returns
    -------
    SaturationVerdict
        ``selected`` is ``None`` whenever the curve has not saturated — an
        unsaturated sweep yields no reportable row, by declaration.
    """
    if not sweep:
        raise ValueError("sweep must hold at least one point")
    if not band > 0.0:
        raise ValueError(f"band must be > 0; got {band!r}")

    ordered = sorted(sweep, key=lambda p: p.rigidity)
    rigidities = [p.rigidity for p in ordered]
    if len(set(rigidities)) != len(rigidities):
        raise ValueError(f"duplicate rigidity values in sweep: {rigidities}")

    maximum = max(ordered, key=lambda p: p.psnr)
    largest = ordered[-1]

    # Has the curve stopped gaining? A one-point sweep cannot demonstrate that it
    # has, so it is treated as unsaturated rather than as trivially converged.
    last_gain = largest.psnr - ordered[-2].psnr if len(ordered) >= 2 else None
    saturated = last_gain is not None and last_gain <= band

    if not saturated:
        continue_at = _next_step(largest.rigidity, continuation_steps)
        hard_stop = continue_at is None
        if last_gain is None:
            # A one-point sweep has no predecessor to have gained over, so the
            # gain cannot appear in the reason at all.
            where = (
                f"continue at rho={continue_at:g}"
                if continue_at is not None
                else f"the continuation ladder is exhausted at "
                f"rho={max(continuation_steps):g}"
            )
            reason = f"a single-point sweep cannot demonstrate saturation; {where}"
        elif hard_stop:
            reason = (
                f"the sweep did not saturate within the declared range: rho="
                f"{largest.rigidity:g} still gains {last_gain:.4f} dB over its "
                f"predecessor, exceeding the {band:.4f} dB band, and the "
                f"continuation ladder is exhausted at rho="
                f"{max(continuation_steps):g}"
            )
        else:
            reason = (
                f"not saturated: rho={largest.rigidity:g} gains {last_gain:.4f} dB "
                f"over its predecessor, exceeding the {band:.4f} dB band; continue "
                f"at rho={continue_at:g}"
            )
        return SaturationVerdict(
            saturated=False,
            selected=None,
            maximum=maximum,
            band=band,
            last_gain=last_gain,
            continue_at=continue_at,
            hard_stop_reached=hard_stop,
            reason=reason,
            within_band=(),
        )

    qualifying = tuple(p for p in ordered if p.psnr >= maximum.psnr - band)
    selected = qualifying[0]  # ordered by rigidity, so this is the smallest
    return SaturationVerdict(
        saturated=True,
        selected=selected,
        maximum=maximum,
        band=band,
        last_gain=last_gain,
        continue_at=None,
        hard_stop_reached=False,
        reason=(
            f"saturated: rho={largest.rigidity:g} gains {last_gain:.4f} dB over its "
            f"predecessor, within the {band:.4f} dB band. Smallest rigidity within "
            f"the band of the maximum ({maximum.psnr:.4f} dB at "
            f"rho={maximum.rigidity:g}) is rho={selected.rigidity:g}"
        ),
        within_band=qualifying,
    )


def _next_step(largest: float, steps: Sequence[float]) -> float | None:
    """The smallest declared step strictly above the largest swept rigidity."""
    for step in sorted(steps):
        if step > largest:
            return step
    return None
