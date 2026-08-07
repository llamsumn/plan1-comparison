#!/usr/bin/env python3
"""make_projection_figure.py — the §6.4 figure: a deformed asset, actually pictured.

    python scripts/make_projection_figure.py

Every other figure this project publishes is a plot of a characterisation grid. The
section that carries the contribution had none at all — a chapter about deforming a
Gaussian splat with no image of a deformed Gaussian splat. The obvious sources were
checked and are all closed: the nine cluster runs wrote empty `renders/` directories,
and the archive's one render-looking figure is a plot built on the trex asset this
repository deliberately excludes.

**This is a projection, not a render, and the distinction is not pedantry.** It scatters
the Gaussian *means* — 23,548 points — through an orthographic camera. There is no
rasteriser, no opacity, no covariance, no view-dependent colour. It shows where the
primitives went, which is exactly what the contribution is about, and it shows nothing
about what the scene would look like. `NOT_A_RENDER` says so on the figure itself,
because a caveat that lives only in a JSON file does not travel with the image once the
image is in a chapter.

Two things regenerate byte-identically and one deliberately does not.

* `out/fig_64_penguin_projection.json` does. Both PLYs are committed, the projection is
  elementwise arithmetic, and the serialiser is canonical.
* The **PNG does not**, and asserting that it did would be this project's oldest mistake
  in a new place. A matplotlib PNG's bytes depend on the matplotlib version, on freetype
  and on platform font rasterisation. The solver diagnostic already shipped a check that
  compared floats bit-for-bit and passed only on the machine that wrote the record — 20
  of its 40 values move between BLAS backends. Pinning PNG bytes would hand an examiner
  a red suite for having a newer matplotlib. What is pinned instead is the *drawn data*:
  each panel records the sha256 of its projected point array, and `render()` refuses to
  draw anything that does not hash to it.

The ARAP solve is not re-run here either. It takes ~19 s and, being a linear solve, is
the one part of this chain that is genuinely BLAS-sensitive. `out/penguin_deformed.ply`
is committed and the solve is *recorded* — command, iterations, convergence, energy —
which is the same discipline the characterisation outputs use.

`matplotlib` is imported inside `render()` on purpose. It is a `test` extra and never a
runtime dependency, so that `pyproject.toml`'s claim about a pure-stdlib decision
surface stays true; importing it at module scope would quietly make this file
un-importable in a bare install.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from arap_core import read_ply
from plan1.provenance import REPO_ROOT, display_path, sha256_file

FIGURE_JSON = REPO_ROOT / "out" / "fig_64_penguin_projection.json"
FIGURE_PNG = REPO_ROOT / "out" / "fig_64_penguin_projection.png"

ORIGINAL_PLY = "data/penguin_original.ply"
DEFORMED_PLY = "out/penguin_deformed.ply"

#: Printed on the figure, stored in the record, and asserted in both places.
NOT_A_RENDER = (
    "Orthographic projection of Gaussian means — not a splat render "
    "(no rasteriser, opacity, covariance or view-dependent colour)."
)

#: The view. Declared rather than defaulted, so that changing it is a visible edit
#: to a committed file and not a silent redraw of a published figure.
AZIMUTH_DEG = 0.0
ELEVATION_DEG = 0.0

#: Coordinates are rounded before they are hashed or drawn. The projection is
#: elementwise arithmetic and therefore bit-reproducible, but the PLY read and the
#: solve upstream of it are not promised to be, and a record that changes in the
#: seventeenth digit is a record that fails on someone else's machine for no reason a
#: reader would care about. Five decimals is far finer than a 1,600-pixel figure can
#: show.
DECIMALS = 5

#: How the deformed asset was produced. Recorded, not re-run — see the module
#: docstring. The statistics are what `run_penguin.py` printed on the run that wrote
#: the committed PLY.
DEFORMATION: dict[str, Any] = {
    "command": (
        "python examples/run_penguin.py "
        "--ply data/penguin_original.ply --out out/penguin_deformed.ply "
        "--k 12 --gamma 50 "
        "--fixed-box -0.25 -0.25 -0.25 0.35 -0.10 0.15 "
        "--handle-box -0.25 0.25 -0.25 0.35 0.40 0.15 "
        "--disp 0.05 0.0 0.0 --max-iters 400"
    ),
    "n_iters": 106,
    "converged": True,
    "energy": [0.210316, 0.003733],
    "n_moving_anchors": 3414,
    "n_fixed_anchors": 3593,
}


# ── the projection ──────────────────────────────────────────────────────────
def rotation(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    """Elevation about x, applied after azimuth about the up axis."""
    a = math.radians(azimuth_deg)
    e = math.radians(elevation_deg)
    r_y = np.array(
        [[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]]
    )
    r_x = np.array(
        [[1.0, 0.0, 0.0], [0.0, math.cos(e), -math.sin(e)], [0.0, math.sin(e), math.cos(e)]]
    )
    return r_x @ r_y


def project(xyz: np.ndarray, azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    """(N, 3) -> (N, 2), orthographic.

    Written as elementwise multiply-add rather than as ``xyz @ R.T`` deliberately.
    A matmul of this shape can dispatch to BLAS, and BLAS backends disagree in the
    last place — which is exactly how the solver diagnostic ended up with a bit-for-bit
    check that only passed on one machine. Elementwise arithmetic is IEEE-defined and
    gives the same bytes everywhere.
    """
    r = rotation(azimuth_deg, elevation_deg)
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    return np.stack(
        [
            x * r[0, 0] + y * r[0, 1] + z * r[0, 2],
            x * r[1, 0] + y * r[1, 1] + z * r[1, 2],
        ],
        axis=1,
    )


def rounded(points: np.ndarray) -> np.ndarray:
    return np.round(points, DECIMALS)


def points_digest(points: np.ndarray) -> str:
    """A stable fingerprint of a drawn point array.

    Serialised through the same canonical text the record uses, so the hash is a fact
    about the numbers rather than about numpy's in-memory layout or dtype.
    """
    text = ";".join(f"{x:.{DECIMALS}f},{y:.{DECIMALS}f}" for x, y in points)
    return hashlib.sha256(text.encode()).hexdigest()


def panel_points(label: str) -> np.ndarray:
    """Re-derive one panel's drawn coordinates from the committed PLY."""
    source = ORIGINAL_PLY if label == "original" else DEFORMED_PLY
    cloud = read_ply(str(REPO_ROOT / source))
    return rounded(project(np.asarray(cloud.xyz, dtype=float), AZIMUTH_DEG, ELEVATION_DEG))


# ── the record ──────────────────────────────────────────────────────────────
def _panel(label: str, source: str) -> dict[str, Any]:
    cloud = read_ply(str(REPO_ROOT / source))
    points = rounded(project(np.asarray(cloud.xyz, dtype=float), AZIMUTH_DEG, ELEVATION_DEG))
    return {
        "label": label,
        "source": source,
        "sha256": sha256_file(REPO_ROOT / source),
        "points_sha256": points_digest(points),
        "n_points": int(points.shape[0]),
        "bounds": [
            round(float(points[:, 0].min()), DECIMALS),
            round(float(points[:, 1].min()), DECIMALS),
            round(float(points[:, 0].max()), DECIMALS),
            round(float(points[:, 1].max()), DECIMALS),
        ],
        "centroid": [
            round(float(points[:, 0].mean()), DECIMALS),
            round(float(points[:, 1].mean()), DECIMALS),
        ],
    }


def build_record() -> dict[str, Any]:
    original = _panel("original", ORIGINAL_PLY)
    deformed = _panel("deformed", DEFORMED_PLY)

    moved = np.linalg.norm(panel_points("deformed") - panel_points("original"), axis=1)
    solve = DEFORMATION
    converged = "converged" if solve["converged"] else "NOT converged"

    return {
        "figure": "fig_64_penguin_projection",
        "what": NOT_A_RENDER,
        "caption": (
            f"ARAP deformation of a 3D Gaussian Splatting asset, {original['n_points']:,} "
            f"primitives. The handle region is displaced by 0.05 along x and the pinned "
            f"region is held; the solve {converged} in {solve['n_iters']} iterations, "
            f"energy {solve['energy'][0]:.6f} to {solve['energy'][-1]:.6f}, monotone "
            f"throughout. Points are Gaussian means under an orthographic camera — this "
            f"is a projection, not a splat render."
        ),
        "view": {"azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG},
        "decimals": DECIMALS,
        "n_gaussians": original["n_points"],
        "panels": [original, deformed],
        "deformation": solve,
        "displacement": {
            "max": round(float(moved.max()), DECIMALS),
            "mean": round(float(moved.mean()), DECIMALS),
            "n_moved": int((moved > 1e-6).sum()),
            "n_still": int((moved < 1e-9).sum()),
        },
        "figure_size_px": [2100, 760],
        "regenerate": "python scripts/make_projection_figure.py",
    }


def dumps_record(record: dict[str, Any]) -> str:
    """Canonical text for the record.

    ``sort_keys`` so a reordered dict is not a diff, and a trailing newline so the file
    is a well-formed text file. Point arrays are never serialised — each panel carries
    the sha256 of its coordinates instead, which is 64 characters rather than half a
    megabyte and cannot be hand-adjusted to agree with a figure it does not describe.
    """
    return json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ── the figure ──────────────────────────────────────────────────────────────
def render(record: dict[str, Any], out_png: Path) -> dict[str, Any]:
    """Draw the figure from the record, refusing to draw data it does not describe.

    ``matplotlib`` is imported here rather than at module scope: it is a `test` extra,
    never a runtime dependency, and this file has to stay importable without it.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    width, height = record["figure_size_px"]
    dpi = 100
    fig, axes = plt.subplots(
        1, 3, figsize=(width / dpi, height / dpi), dpi=dpi, sharex=True, sharey=True
    )

    coordinates: dict[str, np.ndarray] = {}
    drawn: list[str] = []
    for ax, panel in zip(axes, record["panels"]):
        points = panel_points(panel["label"])
        digest = points_digest(points)
        if digest != panel["points_sha256"]:
            raise ValueError(
                f"panel {panel['label']!r} re-derives to {digest}, but the record "
                f"describes {panel['points_sha256']}. The figure would not be a "
                f"picture of the data it claims to be. Regenerate the record."
            )
        coordinates[panel["label"]] = points
        ax.scatter(points[:, 0], points[:, 1], s=1.2, linewidths=0, alpha=0.5, c="#1f4e79")
        ax.set_aspect("equal")
        ax.set_title(panel["label"], fontsize=13)
        ax.set_xlabel("x")
        ax.tick_params(labelsize=8)
        drawn.append(panel["label"])
    axes[0].set_ylabel("y")

    # The third panel is the one that carries the point. Side by side, a 0.05
    # displacement on a 0.6-wide object is a difference a reader has to hunt for by
    # flicking between two blobs. Coloured by how far each primitive travelled, the
    # structure is immediate: the handle region moves, the pinned region is exactly
    # still, and the interior between them varies smoothly rather than in a step —
    # which is what "as-rigid-as-possible" buys and what a per-region rigidity field
    # is defined against.
    moved = np.linalg.norm(coordinates["deformed"] - coordinates["original"], axis=1)
    order = np.argsort(moved)  # least-moved drawn first, so movement is never hidden
    scatter = axes[2].scatter(
        coordinates["deformed"][order, 0],
        coordinates["deformed"][order, 1],
        c=moved[order],
        s=1.2,
        linewidths=0,
        cmap="viridis",
    )
    axes[2].set_aspect("equal")
    axes[2].set_title("displacement magnitude", fontsize=13)
    axes[2].set_xlabel("x")
    axes[2].tick_params(labelsize=8)
    bar = fig.colorbar(scatter, ax=axes[2], fraction=0.046, pad=0.03)
    bar.set_label("|Δ| in the image plane", fontsize=9)
    bar.ax.tick_params(labelsize=8)
    drawn.append("displacement magnitude")

    solve = record["deformation"]
    still = record["displacement"]["n_still"]
    fig.suptitle(
        f"Penguin 3DGS, {record['n_gaussians']:,} Gaussian means — ARAP deformation "
        f"({'converged' if solve['converged'] else 'NOT converged'}, "
        f"{solve['n_iters']} iterations; {solve['n_moving_anchors']:,} handle and "
        f"{solve['n_fixed_anchors']:,} pinned anchors, {still:,} points exactly still)",
        fontsize=13,
    )
    fig.text(0.5, 0.025, NOT_A_RENDER, ha="center", fontsize=9, color="#444444")
    fig.tight_layout(rect=(0, 0.075, 1, 0.96))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    # `metadata` suppresses matplotlib's creation-date tag. The PNG is still not
    # promised byte-identical across matplotlib versions — see the module docstring —
    # but there is no reason to bake a timestamp in on top of that.
    fig.savefig(out_png, dpi=dpi, metadata={"Software": None, "Creation Time": None})
    plt.close(fig)

    return {
        "figure_text": "\n".join(
            [str(fig.texts[0].get_text()) if fig.texts else "", NOT_A_RENDER, *drawn]
        ),
        "panels_drawn": drawn,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, default=FIGURE_JSON)
    parser.add_argument("--png", type=Path, default=FIGURE_PNG)
    args = parser.parse_args()

    record = build_record()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(dumps_record(record))
    render(record, args.png)
    # `display_path` rather than `relative_to`: the green gate rebuilds into a
    # scratch directory so it can diff the data record without leaving a dirty
    # working tree, and `relative_to` raises on anything outside the repository.
    print(f"wrote {display_path(args.json.resolve())}")
    print(f"wrote {display_path(args.png.resolve())}")


if __name__ == "__main__":
    main()
