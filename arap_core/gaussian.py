"""
gaussian.py — 3DGS-specific carries for the ARAP core.

Run **once after** the solver converges, lifting a mesh-vertex ARAP result to a
deformed Gaussian-splat asset.  The only 3DGS-specific module — everything else
in the core is substrate-agnostic.

The operational subtlety: 3DGS stores shape as **(quaternion, scale)**, not a
3×3 covariance matrix.  So the carry must write back ``(q', s')``, not ``Σ'``.
Two paths:

- **Rotation** (``jacobians is None``): scales unchanged, quaternion composes.
  Cheap, exact — what the current rigid ARAP core needs.
- **Affine** (``jacobians`` given): reconstruct Σ, transform, eigendecompose
  back to ``(q', s')``.  Forward-provision for a dense Jacobian field.

Public API
----------
carry_gaussian(rotations, quats, scales, jacobians=None) -> (q', s')
transform_covariances(rotations, covariances, jacobians=None) -> Σ'
extract_quaternion_scale(covariances) -> (q, s)
rotate_sh(rotations, sh_coeffs, degree) -> sh'   (real SH rotation)

Quaternion convention: **(w, x, y, z)** throughout (3DGS / INRIA convention).
Pure NumPy, CPU, float64.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# Quaternion helpers (gate everything on these — a bug here surfaces as a
# confusing failure three functions up)
# --------------------------------------------------------------------------- #
def _quat_to_R(q: np.ndarray) -> np.ndarray:
    """Unit quaternion (w,x,y,z) → rotation matrix.  Batched: (N,4) → (N,3,3)."""
    q = np.asarray(q, dtype=np.float64)
    single = q.ndim == 1
    if single:
        q = q[np.newaxis]

    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]

    R = np.empty((q.shape[0], 3, 3), dtype=np.float64)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z)
    R[:, 0, 1] = 2 * (x * y - w * z)
    R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z)
    R[:, 1, 1] = 1 - 2 * (x * x + z * z)
    R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y)
    R[:, 2, 1] = 2 * (y * z + w * x)
    R[:, 2, 2] = 1 - 2 * (x * x + y * y)

    return R[0] if single else R


def _R_to_quat(R: np.ndarray) -> np.ndarray:
    """Rotation matrix → unit quaternion (w,x,y,z) via Shepperd's method.

    Batched: (N,3,3) → (N,4).  Sign convention: ``w >= 0``.
    """
    R = np.asarray(R, dtype=np.float64)
    single = R.ndim == 2
    if single:
        R = R[np.newaxis]

    N = R.shape[0]
    q = np.empty((N, 4), dtype=np.float64)

    trace = R[:, 0, 0] + R[:, 1, 1] + R[:, 2, 2]

    # Pick the branch with the largest denominator for numerical stability.
    choices = np.stack([
        trace,
        R[:, 0, 0] - R[:, 1, 1] - R[:, 2, 2],
        -R[:, 0, 0] + R[:, 1, 1] - R[:, 2, 2],
        -R[:, 0, 0] - R[:, 1, 1] + R[:, 2, 2],
    ], axis=-1)
    branch = np.argmax(choices, axis=1)

    m = branch == 0
    if m.any():
        s = np.sqrt(trace[m] + 1.0) * 2
        q[m, 0] = 0.25 * s
        q[m, 1] = (R[m, 2, 1] - R[m, 1, 2]) / s
        q[m, 2] = (R[m, 0, 2] - R[m, 2, 0]) / s
        q[m, 3] = (R[m, 1, 0] - R[m, 0, 1]) / s

    m = branch == 1
    if m.any():
        s = np.sqrt(1.0 + R[m, 0, 0] - R[m, 1, 1] - R[m, 2, 2]) * 2
        q[m, 0] = (R[m, 2, 1] - R[m, 1, 2]) / s
        q[m, 1] = 0.25 * s
        q[m, 2] = (R[m, 0, 1] + R[m, 1, 0]) / s
        q[m, 3] = (R[m, 0, 2] + R[m, 2, 0]) / s

    m = branch == 2
    if m.any():
        s = np.sqrt(1.0 + R[m, 1, 1] - R[m, 0, 0] - R[m, 2, 2]) * 2
        q[m, 0] = (R[m, 0, 2] - R[m, 2, 0]) / s
        q[m, 1] = (R[m, 0, 1] + R[m, 1, 0]) / s
        q[m, 2] = 0.25 * s
        q[m, 3] = (R[m, 1, 2] + R[m, 2, 1]) / s

    m = branch == 3
    if m.any():
        s = np.sqrt(1.0 + R[m, 2, 2] - R[m, 0, 0] - R[m, 1, 1]) * 2
        q[m, 0] = (R[m, 1, 0] - R[m, 0, 1]) / s
        q[m, 1] = (R[m, 0, 2] + R[m, 2, 0]) / s
        q[m, 2] = (R[m, 1, 2] + R[m, 2, 1]) / s
        q[m, 3] = 0.25 * s

    norms = np.linalg.norm(q, axis=1, keepdims=True)
    q /= norms
    q[q[:, 0] < 0] *= -1   # sign convention: w >= 0

    return q[0] if single else q


def _compose_quat_rotation(
    R: np.ndarray, q: np.ndarray,
) -> np.ndarray:
    """Compose rotation matrix R with quaternion q: ``quat(R · R(q))``.

    Batched: (N,3,3), (N,4) → (N,4).
    """
    R_q = _quat_to_R(q)                                  # (N, 3, 3)
    R_composed = np.einsum("nij,njk->nik", R, R_q)       # (N, 3, 3)
    return _R_to_quat(R_composed)


# --------------------------------------------------------------------------- #
# Covariance transform (matrix level)
# --------------------------------------------------------------------------- #
def transform_covariances(
    rotations: np.ndarray,
    covariances: np.ndarray,
    jacobians: np.ndarray | None = None,
) -> np.ndarray:
    """Congruence transform: ``Σ' = J Σ Jᵀ``.  Uses ``J = R`` if no Jacobians.

    Parameters
    ----------
    rotations : (N, 3, 3) float64
    covariances : (N, 3, 3) float64   symmetric PSD rest covariances
    jacobians : (N, 3, 3) float64, optional

    Returns
    -------
    (N, 3, 3) float64   deformed Σ', symmetric PSD.
    """
    J = jacobians if jacobians is not None else rotations
    return np.einsum("nij,njk,nlk->nil", J, covariances, J)


# --------------------------------------------------------------------------- #
# Write-back: covariance → storable (quaternion, scale)
# --------------------------------------------------------------------------- #
def extract_quaternion_scale(
    covariances: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Eigendecompose Σ back to storable (quaternion, scale).

    Parameters
    ----------
    covariances : (N, 3, 3) float64   symmetric PSD

    Returns
    -------
    quats  : (N, 4) float64   unit quaternions (w,x,y,z)
    scales : (N, 3) float64   axis lengths >= 0
    """
    eigvals, eigvecs = np.linalg.eigh(covariances)   # ascending eigenvalues
    eigvals = np.maximum(eigvals, 0.0)                # clamp numerical noise
    scales = np.sqrt(eigvals)

    # Ensure eigenvector matrices are proper rotations (det > 0)
    dets = np.linalg.det(eigvecs)
    needs_flip = dets < 0
    if needs_flip.any():
        eigvecs[needs_flip, :, 0] *= -1

    quats = _R_to_quat(eigvecs)
    return quats, scales


# --------------------------------------------------------------------------- #
# Public API: stored representation in → stored representation out
# --------------------------------------------------------------------------- #
def carry_gaussian(
    rotations: np.ndarray,
    quats: np.ndarray,
    scales: np.ndarray,
    jacobians: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Carry Gaussian shape parameters through an ARAP deformation.

    Parameters
    ----------
    rotations : (N, 3, 3) float64   from ``ARAPResult.rotations``
    quats : (N, 4) float64          rest quaternions (w,x,y,z)
    scales : (N, 3) float64         rest axis lengths
    jacobians : (N, 3, 3), optional  general affine; if None, uses rotation path

    Returns
    -------
    quats'  : (N, 4) float64
    scales' : (N, 3) float64

    Notes
    -----
    **Rotation path** (``jacobians is None``): scales unchanged, quaternion
    composed — cheap and exact (verified to 5.6e-17 vs. the matrix route).
    **Affine path**: reconstruct Σ, transform, eigendecompose back to (q', s').
    """
    if jacobians is None:
        quats_new = _compose_quat_rotation(rotations, quats)
        return quats_new, scales.copy()

    # Affine path: reconstruct → transform → re-extract
    R_q = _quat_to_R(quats)                                     # (N, 3, 3)
    s_sq = scales ** 2                                           # (N, 3)
    cov = np.einsum("nij,nj,nkj->nik", R_q, s_sq, R_q)         # R diag(s²) Rᵀ
    cov_new = transform_covariances(rotations, cov, jacobians)
    return extract_quaternion_scale(cov_new)


# --------------------------------------------------------------------------- #
# SH rotation — real spherical-harmonic (Wigner-D) rotation
# --------------------------------------------------------------------------- #
# Real SH basis constants, INRIA/3DGS convention (sh_utils.eval_sh), degrees 0–3.
# These MUST match the coefficient order io_ply reads/writes, so the rotation is
# expressed in the same basis the renderer evaluates.
_SH_C0 = 0.28209479177387814
_SH_C1 = 0.4886025119029199
_SH_C2 = (
    1.0925484305920792,
    -1.0925484305920792,
    0.31539156525252005,
    -1.0925484305920792,
    0.5462742152960396,
)
_SH_C3 = (
    -0.5900435899266435,
    2.890611442640554,
    -0.4570457994644658,
    0.3731763325901154,
    -0.4570457994644658,
    1.445305721320277,
    -0.5900435899266435,
)


def _sh_basis(dirs: np.ndarray, degree: int) -> np.ndarray:
    """Evaluate the real SH basis at directions, INRIA/3DGS convention.

    Parameters
    ----------
    dirs : (..., 3) float64   directions (normalised internally).
    degree : int              band limit, 0–3 (3DGS maximum).

    Returns
    -------
    (..., (degree+1)**2) float64
        Basis values, DC first, in the coefficient order stored by ``io_ply``.
    """
    if degree > 3:
        raise ValueError(f"_sh_basis: degree {degree} > 3 not supported (3DGS max)")
    d = np.asarray(dirs, dtype=np.float64)
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]

    cols = [np.full(x.shape, _SH_C0, dtype=np.float64)]
    if degree >= 1:
        cols += [-_SH_C1 * y, _SH_C1 * z, -_SH_C1 * x]
    if degree >= 2:
        xx, yy, zz = x * x, y * y, z * z
        xy, yz, xz = x * y, y * z, x * z
        cols += [
            _SH_C2[0] * xy,
            _SH_C2[1] * yz,
            _SH_C2[2] * (2.0 * zz - xx - yy),
            _SH_C2[3] * xz,
            _SH_C2[4] * (xx - yy),
        ]
    if degree >= 3:
        cols += [
            _SH_C3[0] * y * (3.0 * xx - yy),
            _SH_C3[1] * xy * z,
            _SH_C3[2] * y * (4.0 * zz - xx - yy),
            _SH_C3[3] * z * (2.0 * zz - 3.0 * xx - 3.0 * yy),
            _SH_C3[4] * x * (4.0 * zz - xx - yy),
            _SH_C3[5] * z * (xx - yy),
            _SH_C3[6] * x * (xx - 3.0 * yy),
        ]
    return np.stack(cols, axis=-1)


def rotate_sh(
    rotations: np.ndarray,
    sh_coeffs: np.ndarray,
    degree: int,
) -> np.ndarray:
    """Rotate per-Gaussian real spherical-harmonic coefficients.

    A Gaussian's view-dependent colour is a band-limited function on the sphere;
    when the Gaussian rotates by ``R`` that function must rotate with it. This
    applies the exact real-SH rotation (real Wigner-D), band by band.

    Method: instead of hand-coding the Ivanic–Ruedenberg recurrence, each band's
    rotation matrix is recovered by least squares from the basis itself — sample
    the band at fixed directions (``B``), evaluate it at the ``R``-rotated
    directions (``B_R``), and solve ``M = B⁺ B_R``. SH bands are closed under
    rotation, so ``M`` is the *exact* rotation matrix, expressed in **the same
    basis** ``_sh_basis`` uses — which matches ``io_ply``'s stored order by
    construction, so there is no convention drift versus the renderer.

    Band 0 (DC) is rotation-invariant and passes through untouched. Gaussians
    whose rotation is (numerically) the identity are copied through **byte-exact**.

    Parameters
    ----------
    rotations : (N, 3, 3) float64   per-Gaussian proper rotations.
    sh_coeffs : (N, n_coeffs, 3) float64   RGB per coefficient; ``[:, 0]`` is DC.
    degree : int   band limit; ``(degree+1)**2`` must equal ``n_coeffs``.

    Returns
    -------
    (N, n_coeffs, 3) float64   rotated coefficients (same shape).
    """
    R = np.asarray(rotations, dtype=np.float64)
    c = np.asarray(sh_coeffs, dtype=np.float64)
    n_coeffs = c.shape[1]
    if (degree + 1) ** 2 != n_coeffs:
        raise ValueError(
            f"rotate_sh: degree {degree} implies {(degree + 1) ** 2} coeffs, "
            f"but sh_coeffs has {n_coeffs}"
        )

    out = c.copy()
    if degree >= 1:
        rng = np.random.default_rng(0)   # fixed → deterministic sample directions
        for l in range(1, degree + 1):
            width = 2 * l + 1
            lo, hi = l * l, (l + 1) ** 2
            dirs = rng.standard_normal((3 * width, 3))
            dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
            B_inv = np.linalg.pinv(_sh_basis(dirs, degree)[:, lo:hi])   # (width, K)
            rot_dirs = np.einsum("kj,nji->nki", dirs, R)               # Rᵀ·dirs (N,K,3)
            B_R = _sh_basis(rot_dirs, degree)[..., lo:hi]              # (N, K, width)
            M = np.einsum("ak,nkb->nab", B_inv, B_R)                   # (N, width, width)
            out[:, lo:hi, :] = np.einsum("nab,nbc->nac", M, c[:, lo:hi, :])

        # Identity rotations → byte-exact passthrough (guards the identity edit).
        is_id = np.all(np.abs(R - np.eye(3)) < 1e-9, axis=(1, 2))
        if is_id.any():
            out[is_id] = c[is_id]

    return out
