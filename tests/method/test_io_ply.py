"""Round-trip and contract tests for arap_core.io_ply (blueprint A.1).

Four checks:
1. Round-trip identity — read(write(cloud)) == cloud to float tolerance.
2. Activation correctness — the raw file stores log(scales) / logit(opacity).
3. Quaternion order — a known rotation survives the (w,x,y,z) boundary as
   the same rotation matrix.
4. Header robustness — a missing property raises a clear error, never a
   silent misparse.
"""

import numpy as np
import pytest
from plyfile import PlyData, PlyElement

from arap_core.io_ply import GaussianCloud, read_ply, write_ply
from arap_core.gaussian import _quat_to_R


def make_cloud(n=100, degree=2, seed=0):
    """Synthetic cloud with float32-representable values (PLY stores f4)."""
    rng = np.random.default_rng(seed)
    n_coeffs = (degree + 1) ** 2

    quats = rng.standard_normal((n, 4))
    quats /= np.linalg.norm(quats, axis=1, keepdims=True)

    cloud = GaussianCloud(
        xyz=rng.uniform(-2, 2, (n, 3)),
        quats=quats,
        scales=rng.uniform(0.05, 1.5, (n, 3)),
        opacity=rng.uniform(0.05, 0.95, n),
        sh=rng.standard_normal((n, n_coeffs, 3)),
    )
    # Snap to float32 so round-trip comparisons are exact-at-tolerance.
    return GaussianCloud(
        **{
            k: np.asarray(getattr(cloud, k), dtype=np.float32).astype(np.float64)
            for k in ("xyz", "quats", "scales", "opacity", "sh")
        }
    )


# ── 1. Round-trip identity ──────────────────────────────────────────────────
def test_round_trip_identity(tmp_path):
    cloud = make_cloud()
    path = str(tmp_path / "rt.ply")
    write_ply(cloud, path)
    back = read_ply(path)

    assert back.n_gaussians == cloud.n_gaussians
    assert back.sh_degree == cloud.sh_degree
    np.testing.assert_allclose(back.xyz, cloud.xyz, atol=1e-6)
    np.testing.assert_allclose(back.scales, cloud.scales, rtol=1e-5)
    np.testing.assert_allclose(back.opacity, cloud.opacity, atol=1e-6)
    np.testing.assert_allclose(back.sh, cloud.sh, atol=1e-6)
    # Quaternions: q and −q are the same rotation; compare matrices.
    np.testing.assert_allclose(
        _quat_to_R(back.quats), _quat_to_R(cloud.quats), atol=1e-6
    )


def test_round_trip_degree_zero(tmp_path):
    """DC-only cloud (no f_rest_*) must round-trip too."""
    cloud = make_cloud(n=10, degree=0)
    path = str(tmp_path / "dc.ply")
    write_ply(cloud, path)
    back = read_ply(path)
    assert back.sh.shape == (10, 1, 3)
    assert back.sh_degree == 0
    np.testing.assert_allclose(back.sh, cloud.sh, atol=1e-6)


# ── 2. Activation correctness ───────────────────────────────────────────────
def test_stored_values_are_preactivation(tmp_path):
    cloud = make_cloud(n=20)
    path = str(tmp_path / "act.ply")
    write_ply(cloud, path)

    raw = PlyData.read(path)["vertex"].data
    stored_scale = np.asarray(raw["scale_0"], dtype=np.float64)
    stored_opacity = np.asarray(raw["opacity"], dtype=np.float64)

    np.testing.assert_allclose(stored_scale, np.log(cloud.scales[:, 0]), atol=1e-5)
    expected_logit = np.log(cloud.opacity / (1 - cloud.opacity))
    np.testing.assert_allclose(stored_opacity, expected_logit, atol=1e-4)

    # Stored quats are unit-norm in (w,x,y,z)
    stored_q = np.column_stack(
        [np.asarray(raw[f"rot_{i}"], dtype=np.float64) for i in range(4)]
    )
    np.testing.assert_allclose(np.linalg.norm(stored_q, axis=1), 1.0, atol=1e-6)


# ── 3. Quaternion order survives the I/O boundary ───────────────────────────
def test_quaternion_order(tmp_path):
    # 90° about z in (w,x,y,z): (cos45°, 0, 0, sin45°)
    s = np.sqrt(0.5)
    q_known = np.array([[s, 0.0, 0.0, s]])
    R_known = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])

    cloud = make_cloud(n=1, degree=0)
    cloud = GaussianCloud(
        xyz=cloud.xyz, quats=q_known, scales=cloud.scales,
        opacity=cloud.opacity, sh=cloud.sh,
    )
    path = str(tmp_path / "quat.ply")
    write_ply(cloud, path)
    back = read_ply(path)

    np.testing.assert_allclose(_quat_to_R(back.quats[0]), R_known, atol=1e-6)


# ── 4. Header robustness: missing property errors clearly ───────────────────
def test_missing_property_raises(tmp_path):
    cloud = make_cloud(n=5)
    good = str(tmp_path / "good.ply")
    write_ply(cloud, good)

    # Rewrite the file without 'opacity'
    v = PlyData.read(good)["vertex"].data
    kept = [n for n in v.dtype.names if n != "opacity"]
    stripped = np.empty(len(v), dtype=[(n, "<f4") for n in kept])
    for n in kept:
        stripped[n] = v[n]
    bad = str(tmp_path / "bad.ply")
    PlyData([PlyElement.describe(stripped, "vertex")], text=False).write(bad)

    with pytest.raises(ValueError, match="opacity"):
        read_ply(bad)


def test_non_contiguous_f_rest_raises(tmp_path):
    cloud = make_cloud(n=5, degree=1)   # f_rest_0..8
    good = str(tmp_path / "good2.ply")
    write_ply(cloud, good)

    v = PlyData.read(good)["vertex"].data
    kept = [n for n in v.dtype.names if n != "f_rest_4"]
    stripped = np.empty(len(v), dtype=[(n, "<f4") for n in kept])
    for n in kept:
        stripped[n] = v[n]
    bad = str(tmp_path / "bad2.ply")
    PlyData([PlyElement.describe(stripped, "vertex")], text=False).write(bad)

    with pytest.raises(ValueError):
        read_ply(bad)
