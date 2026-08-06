"""Seam-2 tests for arap_core.gaussian.rotate_sh — real SH rotation.

Convention-agnostic properties that pin ``rotate_sh`` as a correct real-SH
(Wigner-D) rotation, no renderer required:

  1. identity rotation is a byte-exact no-op
  2. band 0 (DC) is invariant under any rotation
  3. equivariance: eval(rotate(R)·c, d) == eval(c, Rᵀ·d)   [the definitive test]
  4. composition: rotate(R2) ∘ rotate(R1) == rotate(R2·R1)
  5. degree-0 clouds pass through unchanged
"""

import numpy as np

from arap_core.gaussian import rotate_sh, _sh_basis, _quat_to_R


def _rand_rotations(n, seed):
    rng = np.random.default_rng(seed)
    q = rng.standard_normal((n, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return _quat_to_R(q)


def test_identity_is_byte_exact():
    rng = np.random.default_rng(1)
    c = rng.standard_normal((7, 16, 3))
    R = np.tile(np.eye(3), (7, 1, 1))
    out = rotate_sh(R, c, degree=3)
    assert np.array_equal(out, c)


def test_band0_invariant_under_rotation():
    rng = np.random.default_rng(2)
    c = rng.standard_normal((5, 16, 3))
    out = rotate_sh(_rand_rotations(5, 3), c, degree=3)
    np.testing.assert_array_equal(out[:, 0, :], c[:, 0, :])


def test_equivariance_eval_matches_rotated_argument():
    rng = np.random.default_rng(4)
    N = 6
    c = rng.standard_normal((N, 16, 3))
    R = _rand_rotations(N, 5)
    out = rotate_sh(R, c, degree=3)

    dirs = rng.standard_normal((64, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    Y = _sh_basis(dirs, 3)                        # (64, 16)
    for n in range(N):
        lhs = Y @ out[n]                          # eval rotated coeffs at d
        rhs = _sh_basis(dirs @ R[n], 3) @ c[n]    # eval original at Rᵀd
        np.testing.assert_allclose(lhs, rhs, atol=1e-9)


def test_composition_is_homomorphism():
    rng = np.random.default_rng(6)
    c = rng.standard_normal((4, 16, 3))
    R1, R2 = _rand_rotations(4, 7), _rand_rotations(4, 8)
    stepwise = rotate_sh(R2, rotate_sh(R1, c, 3), 3)
    combined = rotate_sh(R2 @ R1, c, 3)
    np.testing.assert_allclose(stepwise, combined, atol=1e-8)


def test_degree_zero_is_noop():
    rng = np.random.default_rng(9)
    c = rng.standard_normal((3, 1, 3))
    out = rotate_sh(_rand_rotations(3, 10), c, degree=0)
    assert np.array_equal(out, c)


def test_deterministic():
    rng = np.random.default_rng(11)
    c = rng.standard_normal((5, 16, 3))
    R = _rand_rotations(5, 12)
    assert np.array_equal(rotate_sh(R, c, 3), rotate_sh(R, c, 3))
