"""§6.4 gets a picture of a deformed asset, and it is honest about what it is.

Every one of the eight vendored figures is a matplotlib plot of a characterisation
grid. §6.4 is the section that carries the contribution and it had no figure at all —
a chapter about deforming a Gaussian splat with no image of a deformed Gaussian splat.

The escape routes were checked and are closed: the nine cluster runs' `renders/`
directories were empty (recorded in `evidence/PROVENANCE.toml`), and
`fig_render_corroboration.png` in the archive is also a plot *and* is built on the trex
asset that `CONTEXT.md` deliberately excludes. Nothing in reach is a rendering.

So this is a **CPU orthographic projection of the Gaussian means** — 23,548 points
scattered on a plane, before and after the solve. It is not a splat render: no
rasteriser, no opacity, no covariance, no view-dependent colour. That distinction is
asserted here and printed on the figure, because a projection that a reader mistakes
for a render is a claim this project has not earned.

**What is asserted byte-identically, and what deliberately is not.**

The projection is pure arithmetic on committed bytes, so `out/fig_64_penguin_projection.json`
regenerates byte-for-byte and that is asserted. The **PNG is not**, and refusing to
assert it is the considered decision rather than a gap. A matplotlib PNG's bytes depend
on the matplotlib version, on freetype, and on the platform's font rasterisation. This
project has already shipped a check that passed only on the machine that wrote the
record — the solver diagnostic compared floats bit-for-bit, and 20 of its 40 values
differ between BLAS backends on identical numpy and scipy. Asserting PNG byte-identity
would be that same mistake with a different file extension, and it would hand an
examiner a red suite for having a newer matplotlib. What is asserted instead is that
the PNG regenerates, is a valid PNG, and has the pixel dimensions the record declares.

For the same reason the ARAP solve is **not** in the test path. `data/penguin_deformed.ply`
is committed and the figure is built from it; the solve that produced it is recorded
with its command and its reported statistics, exactly as the characterisation outputs
are recorded rather than regenerated. Both panels are then re-derived from committed
bytes, which is what makes the record checkable.
"""

from __future__ import annotations

import json
import math
import struct

import numpy as np
import pytest

from plan1.provenance import REPO_ROOT, sha256_file

from scripts.make_projection_figure import (  # noqa: E402
    FIGURE_JSON,
    FIGURE_PNG,
    NOT_A_RENDER,
    build_record,
    dumps_record,
    panel_points,
    points_digest,
    project,
    render,
)

RECORD = json.loads(FIGURE_JSON.read_text())


def panel(label: str) -> dict:
    return next(p for p in RECORD["panels"] if p["label"] == label)


# ── the projection is arithmetic, and it is exact ───────────────────────────
def test_the_identity_view_is_the_plain_xy_drop():
    """Azimuth 0, elevation 0 leaves the points alone and drops z. Exactly — this is
    the case a reader can check by eye, so it is the one pinned to equality."""
    xyz = np.array([[1.0, 2.0, 3.0], [-4.0, 5.0, -6.0], [0.0, 0.0, 0.0]])
    assert np.array_equal(project(xyz, azimuth_deg=0.0, elevation_deg=0.0), xyz[:, :2])


def test_a_quarter_turn_about_the_up_axis_swaps_the_two_horizontal_axes():
    """At azimuth 90 the +z axis comes round to +x and +x goes to -z, so a point on
    +x projects to the origin of the horizontal axis and one on +z projects to +1."""
    on_x = project(np.array([[1.0, 0.0, 0.0]]), 90.0, 0.0)
    on_z = project(np.array([[0.0, 0.0, 1.0]]), 90.0, 0.0)
    assert on_x[0, 0] == pytest.approx(0.0, abs=1e-12)
    assert on_z[0, 0] == pytest.approx(1.0, abs=1e-12)


def test_elevation_tilts_the_vertical_axis_and_nothing_else():
    up = project(np.array([[0.0, 1.0, 0.0]]), 0.0, 90.0)
    assert up[0, 0] == pytest.approx(0.0, abs=1e-12)
    assert up[0, 1] == pytest.approx(0.0, abs=1e-12)


def test_the_projection_preserves_every_point():
    xyz = np.arange(30, dtype=float).reshape(10, 3)
    assert project(xyz, 30.0, 20.0).shape == (10, 2)


def test_the_projection_is_deterministic_within_a_process():
    """The weakest possible version of the claim, and still worth pinning: nothing
    here reads a clock, a seed or a hash-randomised iteration order."""
    xyz = np.arange(300, dtype=float).reshape(100, 3) * 0.017
    assert np.array_equal(project(xyz, 41.0, 17.0), project(xyz, 41.0, 17.0))


def test_an_orthographic_projection_does_not_change_distances_in_its_own_plane():
    """A projection is a rotation followed by dropping a coordinate. Points that
    differ only within the image plane keep their separation; that is what makes the
    picture a faithful shape rather than a perspective impression of one."""
    a = project(np.array([[0.0, 0.0, 0.0]]), 33.0, 21.0)
    b = project(np.array([[0.0, 1.0, 0.0]]), 33.0, 21.0)
    c = project(np.array([[0.0, 2.0, 0.0]]), 33.0, 21.0)
    assert np.linalg.norm(b - a) == pytest.approx(np.linalg.norm(c - b), abs=1e-12)


# ── the committed record re-derives from committed bytes ────────────────────
def test_the_record_regenerates_byte_identically():
    """The claim the table makes, made again for the figure's data.

    Both source PLYs are in the repository, the projection is arithmetic, and the
    serialiser is canonical — so there is no excuse for this to be anything but exact.
    """
    assert dumps_record(build_record()) == FIGURE_JSON.read_text()


def test_the_serialiser_is_canonical_so_a_hand_edit_shows_up():
    assert dumps_record(RECORD) == FIGURE_JSON.read_text()


@pytest.mark.parametrize("label", ["original", "deformed"])
def test_each_panel_carries_every_gaussian(label):
    assert panel(label)["n_points"] == RECORD["n_gaussians"] == 23548
    assert len(panel_points(label)) == 23548


@pytest.mark.parametrize("label", ["original", "deformed"])
def test_each_panel_names_the_ply_it_was_projected_from_and_that_hash_is_right(label):
    """Binds the figure to file content rather than to a path, the same way the
    upstream diffs are bound to the hashes the evidence record holds."""
    assert sha256_file(REPO_ROOT / panel(label)["source"]) == panel(label)["sha256"]


@pytest.mark.parametrize("label", ["original", "deformed"])
def test_each_panel_pins_the_coordinates_that_were_actually_drawn(label):
    """The record holds a hash of the point array rather than the array.

    Sixty-four characters instead of half a megabyte, and — unlike a committed copy of
    the numbers — it cannot be nudged into agreeing with a figure it does not describe.
    `render()` recomputes it and refuses to draw on a mismatch.
    """
    assert points_digest(panel_points(label)) == panel(label)["points_sha256"]


def test_the_two_panels_are_actually_different():
    """A figure of a deformation where nothing moved is the failure that would look
    completely normal — the identity check `run_penguin.py` runs writes exactly that
    file on purpose. The handle box was displaced by 0.05, so something has to move."""
    moved = np.linalg.norm(panel_points("deformed") - panel_points("original"), axis=1)
    assert moved.max() > 0.01, moved.max()
    assert (moved > 1e-6).sum() > 1000, "the deformation barely touched anything"


def test_the_pinned_region_did_not_move():
    """The other half of the same check, and the one that would catch a solve that
    moved the whole object rather than deforming it. Some points are anchored."""
    moved = np.linalg.norm(panel_points("deformed") - panel_points("original"), axis=1)
    assert (moved < 1e-9).sum() > 100, "nothing stayed put — is this a rigid transform?"


def test_exactly_the_pinned_anchors_are_the_points_that_did_not_move():
    """An invariant nobody designed for, which is why it is worth pinning.

    3,593 primitives are exactly still and `run_penguin.py` reported 3,593 fixed
    anchors. Those are independent numbers — one is the solver's constraint set, the
    other is measured off the written geometry after a PLY round-trip — and their
    agreement says the pinned region really was pinned, to the bit, rather than
    approximately held.

    It is exact only because this view drops z and no point moved purely along it; a
    changed view angle could legitimately break it. That is a reason to re-derive the
    number, not to weaken the check, so the equality is asserted and the caveat
    written down.
    """
    moved = np.linalg.norm(panel_points("deformed") - panel_points("original"), axis=1)
    assert int((moved == 0.0).sum()) == RECORD["deformation"]["n_fixed_anchors"]


def test_the_recorded_displacement_summary_is_the_one_the_geometry_has():
    """The record publishes max, mean and how many points moved. Read back out of the
    PLYs rather than trusted, so the caption cannot outlive the geometry."""
    moved = np.linalg.norm(panel_points("deformed") - panel_points("original"), axis=1)
    summary = RECORD["displacement"]
    assert round(float(moved.max()), RECORD["decimals"]) == summary["max"]
    assert round(float(moved.mean()), RECORD["decimals"]) == summary["mean"]
    assert int((moved > 1e-6).sum()) == summary["n_moved"]


# ── it says what it is ──────────────────────────────────────────────────────
def test_the_record_declares_that_this_is_not_a_render():
    assert RECORD["what"] == NOT_A_RENDER
    for owed in ("projection", "not a splat render"):
        assert owed in NOT_A_RENDER.lower()


def test_the_disclaimer_survives_onto_the_figure_itself(tmp_path):
    """A caveat that lives only in a JSON file beside the image does not travel with
    the image. Once the PNG is in a chapter it is on its own, so the words are drawn
    into it."""
    png = tmp_path / "fig.png"
    drawn = render(RECORD, png)
    assert NOT_A_RENDER in drawn["figure_text"]


def test_the_record_names_the_command_that_produced_the_deformation():
    """The solve is not re-run here, so it is recorded instead — the discipline the
    characterisation outputs already use. Without the command the deformed PLY is a
    file that appeared."""
    solve = RECORD["deformation"]
    assert solve["command"].startswith("python examples/run_penguin.py")
    assert "--disp 0.05" in solve["command"]
    assert solve["n_iters"] > 0
    assert isinstance(solve["converged"], bool)
    assert solve["energy"][0] > solve["energy"][-1], "the solve did not reduce energy"


def test_the_caption_states_the_convergence_status_either_way():
    """`run_penguin.py` reports `converged`, and a figure that quietly omits it when
    the answer is inconvenient is the failure worth guarding. The caption says which
    it was unconditionally, so the honest branch is not the one that needs remembering.
    """
    solve = RECORD["deformation"]
    expected = "converged" if solve["converged"] else "NOT converged"
    assert f"solve {expected} in {solve['n_iters']} iterations" in RECORD["caption"]


def test_the_figure_would_refuse_to_draw_data_the_record_does_not_describe(tmp_path):
    """The guard that makes `points_sha256` load-bearing rather than decorative."""
    tampered = json.loads(json.dumps(RECORD))
    tampered["panels"][1]["points_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="re-derives to"):
        render(tampered, tmp_path / "fig.png")


# ── the PNG regenerates, and is checked for what a PNG can be checked for ───
def test_the_figure_regenerates_and_is_a_valid_png(tmp_path):
    png = tmp_path / "fig.png"
    render(RECORD, png)
    raw = png.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    assert [width, height] == RECORD["figure_size_px"]


def test_the_committed_png_is_the_one_the_record_describes():
    """Not byte-identity — see this module's docstring for why that would be the
    wrong assertion. Dimensions and PNG validity are what survive a matplotlib
    upgrade, and they still catch a stale or truncated commit."""
    raw = FIGURE_PNG.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    assert [width, height] == RECORD["figure_size_px"]


def test_matplotlib_is_a_test_dependency_and_not_a_runtime_one():
    """The pyproject comment claims the decision surface is pure stdlib and the
    runtime needs only numpy, scipy and plyfile. A plotting library in `dependencies`
    would quietly make that false, so the placement is asserted rather than trusted.
    """
    import tomllib

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert "matplotlib" not in pyproject["project"]["dependencies"]
    assert "matplotlib" in pyproject["project"]["optional-dependencies"]["test"]


def test_the_figure_module_does_not_import_matplotlib_at_module_scope():
    """`plan1` and the assembler must stay importable without a plotting stack.

    Asserted by parsing rather than by importing, because this test module has
    already imported the file and a runtime check would pass on the import cache.
    """
    import ast

    source = (REPO_ROOT / "scripts" / "make_projection_figure.py").read_text()
    tree = ast.parse(source)
    top_level = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    names = {
        alias.name.split(".")[0]
        for node in top_level
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in top_level
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "matplotlib" not in names, names


def test_the_figure_lands_in_out_beside_the_other_published_artefact():
    """`out/` is what this repository publishes and regenerates. The figure belongs
    with the table, not under `evidence/`, which is copies of things from elsewhere."""
    for path in (FIGURE_PNG, FIGURE_JSON):
        assert path.parent == REPO_ROOT / "out"
        assert path.is_file(), path


def test_the_angles_are_declared_rather_than_left_to_a_default():
    """A view angle changed by a later edit silently redraws the published figure."""
    view = RECORD["view"]
    assert isinstance(view["azimuth_deg"], (int, float))
    assert isinstance(view["elevation_deg"], (int, float))
    assert math.isfinite(view["azimuth_deg"]) and math.isfinite(view["elevation_deg"])
