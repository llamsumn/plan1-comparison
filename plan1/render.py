"""render.py — presentation, above the seam.

Turns an assembled table into Markdown. Nothing here decides anything: no
selection, no arithmetic, no gating. It only refuses to print more precision than
a source actually recorded.
"""

from __future__ import annotations

from plan1.assemble import ComparisonTable, GapFraction
from plan1.provenance import display_path
from plan1.records import METRICS, Measurement

#: Display precision per metric, capped by what the source recorded.
DISPLAY_DECIMALS = {"psnr": 3, "ssim": 4, "lpips": 4}

_HEADS = {"psnr": "PSNR", "ssim": "SSIM", "lpips": "LPIPS"}


def format_measurement(m: Measurement, metric: str) -> str:
    """Never print a digit the source does not have."""
    default = DISPLAY_DECIMALS[metric]
    decimals = default if m.decimals is None else min(m.decimals, default)
    return f"{m.value:.{decimals}f}"


def format_fraction(f: GapFraction) -> str:
    if f.exact:
        return f"{f.value * 100:.1f}%"
    return f"{f.value * 100:.1f}% [{f.low * 100:.1f}–{f.high * 100:.1f}%]"


def render_markdown(table: ComparisonTable, provenance: dict[str, str] | None = None) -> str:
    lines: list[str] = []
    out = lines.append

    out(f"# {table.asset} — imposed rigidity against the DeformSplat baseline")
    out("")
    out(
        f"_Assembled {table.assembled} by `plan1.assemble` from the manifest "
        f"at `{display_path(table.manifest_source)}`. Every number below traces to a "
        f"named run; see Provenance. Rules pre-registered in "
        f"`all_record/deformsplat_corroboration/plan1_prereg.md`._"
    )
    out("")

    # ── the table ───────────────────────────────────────────────────────────
    out("| rigidity source | information used | " + " | ".join(_HEADS[m] for m in METRICS) + " |")
    out("|---|---|" + "---|" * len(METRICS))
    out(
        "| *shared start (step 0)* | — | "
        + " | ".join(format_measurement(table.start[m], m) for m in METRICS)
        + " |"
    )
    for row in table.rows:
        if row.role == "null_replicate":
            continue  # reported beneath the table, with the band
        out(
            f"| {row.label} | {row.information} | "
            + " | ".join(format_measurement(row.metrics[m], m) for m in METRICS)
            + " |"
        )

    selected = table.selected_row
    if selected is not None:
        out(
            f"| **fraction of the gap recovered** (at {selected.label}) | | "
            + " | ".join(format_fraction(selected.fractions[m]) for m in METRICS)  # type: ignore[index]
            + " |"
        )
    out("")

    # ── what the rule decided ───────────────────────────────────────────────
    if table.saturation is not None:
        verdict = "SATURATED" if table.saturation.saturated else "NOT SATURATED"
        out(f"**Saturation rule — {verdict}.** {table.saturation.reason}.")
        out("")
        if not table.saturation.saturated:
            out(
                "> No gap-recovered fraction is published while the sweep is "
                "unsaturated. The rule was declared before the runs and is what "
                "selects the reported row."
            )
            out("")

    # ── the full sweep, disclosed ───────────────────────────────────────────
    swept = [r for r in table.rows if r.rigidity is not None]
    if swept:
        out("**Full imposed sweep** (selection is disclosed, not hidden):")
        out("")
        out("| ρ | role | PSNR |")
        out("|---|---|---|")
        for row in sorted(swept, key=lambda r: (r.rigidity, r.key)):
            out(
                f"| {row.rigidity:g} | {row.role} | "
                f"{format_measurement(row.metrics['psnr'], 'psnr')} |"
            )
        out("")

    # ── the null family ─────────────────────────────────────────────────────
    family = [r for r in table.rows if r.role in ("null", "null_replicate")]
    if len(family) > 1:
        out(
            "**The no-rigidity configuration was run "
            f"{len(family)} times** (PSNR "
            + ", ".join(format_measurement(r.metrics["psnr"], "psnr") for r in family)
            + f"); replicate band **{table.band:.4f} dB**, derived from "
            + ", ".join(f"`{k}`" for k in table.band_source)
            + "."
        )
        out("")

    # ── limitations, at the point of the claim ──────────────────────────────
    out("## Limitations")
    out("")
    for note in table.notes:
        out(f"- {note}")
    out(
        "- Single asset, single evaluation camera, single seed per setting. Nothing "
        "here establishes that the result generalises to another object."
    )
    out(
        "- The baseline observes the object's motion; this method does not. Exceeding "
        "it on reconstruction fidelity is not a goal and is not claimed."
    )
    out("")

    # ── provenance ──────────────────────────────────────────────────────────
    out("## Provenance")
    out("")
    out(f"Evaluation step {table.eval_step}; {table.num_primitives} primitives in every row.")
    out("")
    out("| row | source |")
    out("|---|---|")
    for row in table.rows:
        out(f"| `{row.key}` | {row.provenance} |")
    out("")
    if provenance:
        out("| artefact | identity |")
        out("|---|---|")
        for name, value in provenance.items():
            out(f"| {name} | `{value}` |")
        out("")
    return "\n".join(lines)
