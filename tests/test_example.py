"""Does the worked example still run?

`examples/run_penguin.py` is the one file on the claim surface that neither
computes a published number nor generates an artefact the gate diffs. Everything
else is covered one of those two ways — the table and the figure record are
rebuilt from scratch and compared byte for byte, which is a stricter check than
line coverage rather than a weaker one. The example has neither, so "does it
still run?" was genuinely unchecked, and the README quotes a number it printed.

An example that has stopped running is a particular kind of broken: it is the
first thing a reader executes, it is the shortest description of what the library
is for, and it fails in front of the person least able to tell whether the
failure is theirs.

**The penguin does not appear here.** The real asset is 23,548 Gaussians and a
19-second solve, and paying that on every test run to learn that eight function
calls are still wired together would be a bad trade. The cloud below is 125
Gaussians on a lattice, and it drives the identical path: read → knn_edges →
build_graph → make_anchors → arap_solve → carry_gaussian → write_ply.

It is a smoke test and it is labelled as one. It does not check the deformation
is correct — `tests/method/` does that, at the level where correctness is a
property of a function rather than of a script.
"""

import importlib.util
import sys

import numpy as np
import pytest

from arap_core.io_ply import GaussianCloud, read_ply, write_ply
from plan1.provenance import REPO_ROOT

EXAMPLE = REPO_ROOT / "examples" / "run_penguin.py"


def load_example():
    """Import the example by path.

    `examples/` is not a package — deliberately, since the script is meant to be
    run rather than imported — so this is how a test reaches `main()`. Loading it
    fresh per test keeps the module's own import side effects inside the test
    that caused them.
    """
    spec = importlib.util.spec_from_file_location("run_penguin_under_test", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tiny_ply(tmp_path):
    """A 5×5×5 lattice written as a valid degree-0 3DGS `.ply`.

    A lattice rather than a random cloud so the two boxes below select opposite
    faces exactly, and connectivity at k=6 is a fact about the geometry rather
    than about a seed.
    """
    axis = np.linspace(0.0, 1.0, 5)
    xyz = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    n = xyz.shape[0]

    cloud = GaussianCloud(
        xyz=xyz,
        quats=np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (n, 1)),
        scales=np.full((n, 3), 0.05),
        opacity=np.full(n, 0.5),
        sh=np.zeros((n, 1, 3)),
    )
    path = tmp_path / "lattice.ply"
    write_ply(cloud, str(path))
    return path


@pytest.fixture
def run(tmp_path, tiny_ply, monkeypatch):
    """Run the example's `main()` with a command line substituted for argv."""

    def invoke(*extra):
        out = tmp_path / "deformed.ply"
        argv = [
            "run_penguin.py",
            "--ply", str(tiny_ply),
            "--out", str(out),
            "--k", "6",
            "--gamma", "5",
            "--fixed-box", "-0.1", "-0.1", "-0.1", "0.1", "1.1", "1.1",
            "--handle-box", "0.9", "-0.1", "-0.1", "1.1", "1.1", "1.1",
            "--max-iters", "5",
            *extra,
        ]
        monkeypatch.setattr(sys, "argv", argv)
        load_example().main()
        return out

    return invoke


def test_the_example_runs_end_to_end_and_writes_a_readable_ply(run, capsys):
    """The whole point of the module. Eight calls, in order, on a real file."""
    out = run("--disp", "0.1", "0.0", "0.0")

    assert out.is_file()
    back = read_ply(str(out))
    assert back.n_gaussians == 125
    assert np.all(np.isfinite(back.xyz))

    printed = capsys.readouterr().out
    for stage in ("[read ]", "[graph]", "[edit ]", "[solve]", "[carry]", "[write]"):
        assert stage in printed, stage


def test_the_zero_displacement_identity_check_still_holds(run):
    """The example's own documented guard, run as a test.

    Its docstring says a zero displacement must leave the output visually
    identical to the input, and calls that the check on the whole
    read → carry → write chain. It is the one assertion the script makes about
    itself, so it is the one worth holding it to."""
    out = run("--disp", "0.0", "0.0", "0.0")

    back = read_ply(str(out))
    axis = np.linspace(0.0, 1.0, 5)
    expected = np.stack(
        np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1
    ).reshape(-1, 3)

    np.testing.assert_allclose(back.xyz, expected, atol=1e-5)


def test_the_example_runs_without_a_fixed_region(tmp_path, tiny_ply, monkeypatch):
    """`--fixed-box` is optional, and leaving it out takes the other branch of the
    anchor construction — the one `select.py` warns about, because nothing is
    pinned and the deformation is then a translation."""
    out = tmp_path / "unpinned.ply"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_penguin.py",
            "--ply", str(tiny_ply),
            "--out", str(out),
            "--k", "6",
            "--handle-box", "0.9", "-0.1", "-0.1", "1.1", "1.1", "1.1",
            "--disp", "0.05", "0.0", "0.0",
            "--max-iters", "3",
        ],
    )

    with pytest.warns(UserWarning, match="No fixed region given"):
        load_example().main()

    assert out.is_file()


def test_a_disconnected_graph_is_reported_rather_than_solved_silently(
    tmp_path, monkeypatch, capsys
):
    """Two blobs far apart, at a k too small to bridge them. The example prints a
    warning and carries on, which is the right behaviour for a demo — but only if
    it prints. An island that quietly does not follow the deformation is the
    failure mode a reader would blame on the method."""
    axis = np.linspace(0.0, 0.3, 3)
    blob = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    xyz = np.vstack([blob, blob + np.array([50.0, 0.0, 0.0])])
    n = xyz.shape[0]

    cloud = GaussianCloud(
        xyz=xyz,
        quats=np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (n, 1)),
        scales=np.full((n, 3), 0.05),
        opacity=np.full(n, 0.5),
        sh=np.zeros((n, 1, 3)),
    )
    ply = tmp_path / "two-blobs.ply"
    write_ply(cloud, str(ply))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_penguin.py",
            "--ply", str(ply),
            "--out", str(tmp_path / "blobs-out.ply"),
            "--k", "4",
            "--fixed-box", "-0.1", "-0.1", "-0.1", "0.05", "0.4", "0.4",
            "--handle-box", "49.9", "-0.1", "-0.1", "50.05", "0.4", "0.4",
            "--disp", "0.05", "0.0", "0.0",
            "--max-iters", "3",
        ],
    )
    with pytest.warns(UserWarning, match="connected components"):
        load_example().main()

    assert "disconnected graph" in capsys.readouterr().out
