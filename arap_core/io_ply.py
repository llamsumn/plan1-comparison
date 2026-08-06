"""
io_ply.py — 3DGS PLY read/write bridge.

The 3DGS ``.ply`` is **not** a plain point cloud.  It stores per-Gaussian
attributes under specific property names, several in a **pre-activation**
space.  Getting the activations or quaternion order wrong makes a reload look
corrupted:

    scales  : stored as log(s)       → exp on read,   log on write
    opacity : stored as logit(α)     → sigmoid on read, logit on write
    quats   : stored raw (w,x,y,z)   → normalise on read and write

Quaternion order: the INRIA ``.ply`` stores **(w,x,y,z)** — the same
convention ``gaussian.py`` uses internally, so no reorder happens here.
(``scipy.spatial.transform.Rotation`` uses (x,y,z,w); if scipy ever enters
this module, convert at that call site and document it.)

SH layout: ``f_dc_0..2`` is the per-channel RGB DC term.  ``f_rest_0..K-1``
with ``K = 3·((deg+1)² − 1)`` holds the higher bands **channel-major**
(all R coefficients, then all G, then all B) — matching the INRIA layout at
commit ``54c035f``.

The parser maps property names from the actual header and errors loudly if an
expected property is missing — it never trusts the layout blindly.

Public API
----------
read_ply(path) -> GaussianCloud
write_ply(cloud, path) -> None
GaussianCloud — the single currency between io, the solver and the carry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from plyfile import PlyData, PlyElement


# --------------------------------------------------------------------------- #
# The single currency passed between io_ply, the driver, and the carry
# --------------------------------------------------------------------------- #
@dataclass
class GaussianCloud:
    """A 3DGS asset in **usable** (post-activation) space.

    Attributes
    ----------
    xyz : (N, 3) float64      Gaussian centres.
    quats : (N, 4) float64    unit quaternions, **(w, x, y, z)**.
    scales : (N, 3) float64   axis lengths in **linear** space (post-exp), > 0.
    opacity : (N,) float64    post-sigmoid, in (0, 1).
    sh : (N, n_coeffs, 3) float64   RGB per SH coefficient; ``sh[:, 0]`` is DC.
    """

    xyz: np.ndarray
    quats: np.ndarray
    scales: np.ndarray
    opacity: np.ndarray
    sh: np.ndarray

    @property
    def n_gaussians(self) -> int:
        return self.xyz.shape[0]

    @property
    def sh_degree(self) -> int:
        deg_p1 = int(round(math.sqrt(self.sh.shape[1])))
        return deg_p1 - 1


# --------------------------------------------------------------------------- #
# Activations
# --------------------------------------------------------------------------- #
def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p: np.ndarray) -> np.ndarray:
    # Clamp away from {0, 1} so hand-constructed clouds with saturated
    # opacities don't write ±inf into the file.
    eps = 1e-7
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
_REQUIRED = (
    "x", "y", "z",
    "rot_0", "rot_1", "rot_2", "rot_3",
    "scale_0", "scale_1", "scale_2",
    "opacity",
    "f_dc_0", "f_dc_1", "f_dc_2",
)


def read_ply(path: str) -> GaussianCloud:
    """Read a 3DGS ``.ply`` into a :class:`GaussianCloud`.

    Parses the header, maps property names programmatically, applies the
    activations (``exp`` scales, ``sigmoid`` opacity, normalise quats) and
    assembles ``sh`` from ``f_dc_*`` + ``f_rest_*``.

    Raises
    ------
    ValueError
        If an expected property is missing, the ``f_rest_*`` block is
        malformed, or any quaternion has zero norm.  Errors are explicit —
        never a silent misparse.
    """
    ply = PlyData.read(path)

    element_names = [el.name for el in ply.elements]
    if "vertex" not in element_names:
        raise ValueError(
            f"{path}: no 'vertex' element in PLY (found {element_names})"
        )

    v = ply["vertex"].data
    names = set(v.dtype.names)

    missing = [n for n in _REQUIRED if n not in names]
    if missing:
        raise ValueError(
            f"{path}: missing expected 3DGS properties {missing}; "
            f"header has {sorted(names)}"
        )

    def col(name: str) -> np.ndarray:
        return np.asarray(v[name], dtype=np.float64)

    N = len(v)

    # -- positions ---------------------------------------------------------
    xyz = np.column_stack([col("x"), col("y"), col("z")])

    # -- quaternions: raw (w,x,y,z), not guaranteed normalised --------------
    quats = np.column_stack([col(f"rot_{i}") for i in range(4)])
    norms = np.linalg.norm(quats, axis=1)
    if np.any(norms < 1e-12):
        bad = int(np.argmin(norms))
        raise ValueError(f"{path}: zero-norm quaternion at Gaussian {bad}")
    quats = quats / norms[:, np.newaxis]

    # -- scales: stored log, activate with exp ------------------------------
    scales = np.exp(np.column_stack([col(f"scale_{i}") for i in range(3)]))

    # -- opacity: stored logit, activate with sigmoid ------------------------
    opacity = _sigmoid(col("opacity"))

    # -- SH: f_dc_* is band 0; f_rest_* holds bands 1+ channel-major ---------
    n_rest = sum(1 for n in names if n.startswith("f_rest_"))
    for i in range(n_rest):
        if f"f_rest_{i}" not in names:
            raise ValueError(
                f"{path}: f_rest_* block not contiguous — "
                f"{n_rest} properties but f_rest_{i} missing"
            )
    if n_rest % 3 != 0:
        raise ValueError(
            f"{path}: {n_rest} f_rest_* properties is not divisible by 3"
        )

    m = n_rest // 3                      # higher-band coeffs per channel
    n_coeffs = m + 1
    deg_p1 = int(round(math.sqrt(n_coeffs)))
    if deg_p1 * deg_p1 != n_coeffs:
        raise ValueError(
            f"{path}: {n_coeffs} SH coefficients is not a perfect square — "
            f"not a valid band structure"
        )

    dc = np.column_stack([col(f"f_dc_{c}") for c in range(3)])   # (N, 3)
    sh = np.empty((N, n_coeffs, 3), dtype=np.float64)
    sh[:, 0, :] = dc
    if m > 0:
        rest = np.column_stack([col(f"f_rest_{i}") for i in range(n_rest)])
        # channel-major (N, 3, m) → (N, m, 3)
        sh[:, 1:, :] = rest.reshape(N, 3, m).transpose(0, 2, 1)

    return GaussianCloud(
        xyz=xyz, quats=quats, scales=scales, opacity=opacity, sh=sh,
    )


# --------------------------------------------------------------------------- #
# Write
# --------------------------------------------------------------------------- #
def write_ply(cloud: GaussianCloud, path: str) -> None:
    """Write a :class:`GaussianCloud` as a 3DGS ``.ply``.

    Inverts the activations (``log`` scales, ``logit`` opacity, renormalise
    quats), flattens ``sh`` back to ``f_dc_*``/``f_rest_*`` channel-major, and
    writes binary-little-endian with the INRIA property names and order —
    loadable by the INRIA/gsplat renderer and SuperSplat.
    """
    N = cloud.n_gaussians
    n_coeffs = cloud.sh.shape[1]
    m = n_coeffs - 1

    if np.any(cloud.scales <= 0):
        bad = int(np.argmin(cloud.scales.min(axis=1)))
        raise ValueError(
            f"scales must be > 0 in linear space (Gaussian {bad}: "
            f"{cloud.scales[bad]}) — cannot take log for storage"
        )

    quats = cloud.quats / np.linalg.norm(cloud.quats, axis=1, keepdims=True)
    log_scales = np.log(cloud.scales)
    logit_opacity = _logit(np.asarray(cloud.opacity, dtype=np.float64))

    dc = cloud.sh[:, 0, :]                                       # (N, 3)
    rest = cloud.sh[:, 1:, :].transpose(0, 2, 1).reshape(N, 3 * m)  # channel-major

    # INRIA property order at commit 54c035f (normals present, zeroed).
    prop_names = (
        ["x", "y", "z", "nx", "ny", "nz"]
        + [f"f_dc_{c}" for c in range(3)]
        + [f"f_rest_{i}" for i in range(3 * m)]
        + ["opacity"]
        + [f"scale_{i}" for i in range(3)]
        + [f"rot_{i}" for i in range(4)]
    )

    arr = np.empty(N, dtype=[(n, "<f4") for n in prop_names])
    arr["x"], arr["y"], arr["z"] = cloud.xyz[:, 0], cloud.xyz[:, 1], cloud.xyz[:, 2]
    arr["nx"] = arr["ny"] = arr["nz"] = np.zeros(N, dtype=np.float32)
    for c in range(3):
        arr[f"f_dc_{c}"] = dc[:, c]
    for i in range(3 * m):
        arr[f"f_rest_{i}"] = rest[:, i]
    arr["opacity"] = logit_opacity
    for i in range(3):
        arr[f"scale_{i}"] = log_scales[:, i]
    for i in range(4):
        arr[f"rot_{i}"] = quats[:, i]

    element = PlyElement.describe(arr, "vertex")
    PlyData([element], text=False, byte_order="<").write(path)
