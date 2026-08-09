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
import pytest

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


# ── the band structure, at every degree and past the end of it ──────────────
# The five properties above all run at degree 3, which is the maximum and the
# only degree that builds every block of the basis. That left the lower degrees
# unexercised: `_sh_basis` accumulates its columns behind three `degree >= n`
# tests, and a basis truncated at the wrong band would still satisfy every
# property above when asked for the full one.
@pytest.mark.parametrize("degree, width", [(0, 1), (1, 4), (2, 9), (3, 16)])
def test_the_basis_has_one_column_per_coefficient_at_each_degree(degree, width):
    """`(degree + 1)²` columns, which is the identity that lets `rotate_sh` slice
    band `n` out at a fixed offset. Getting this wrong shifts every band above
    the mistake."""
    rng = np.random.default_rng(13)
    dirs = rng.standard_normal((20, 3))

    Y = _sh_basis(dirs, degree)

    assert Y.shape == (20, (degree + 1) ** 2)
    assert Y.shape[1] == width


@pytest.mark.parametrize("degree", [0, 1, 2])
def test_a_lower_degree_basis_is_a_prefix_of_a_higher_one(degree):
    """The property that makes the offsets in `rotate_sh` correct: bands are
    appended, never reordered, so the first `(d+1)²` columns of the degree-3
    basis are exactly the degree-`d` basis. Asserted rather than assumed, because
    the coefficient order has to match what `io_ply` stores and a renderer
    evaluates."""
    rng = np.random.default_rng(14)
    dirs = rng.standard_normal((12, 3))

    full = _sh_basis(dirs, 3)
    truncated = _sh_basis(dirs, degree)

    np.testing.assert_allclose(truncated, full[:, : (degree + 1) ** 2], atol=1e-12)


def test_a_degree_above_the_3dgs_maximum_is_refused():
    """3DGS stores at most degree 3, and the constants above stop there. A
    degree-4 request would otherwise return a degree-3 basis and be silently one
    band short."""
    with pytest.raises(ValueError, match="degree 4 > 3 not supported"):
        _sh_basis(np.array([[0.0, 0.0, 1.0]]), 4)


@pytest.mark.parametrize("degree", [1, 2])
def test_rotate_sh_refuses_a_degree_that_contradicts_the_coefficients(degree):
    """`degree` and the coefficient count are two statements of the same fact, so
    disagreement means one of them is wrong and there is no way to tell which.
    The array here holds 16 coefficients — degree 3 — and is offered as
    something else."""
    rng = np.random.default_rng(15)
    c = rng.standard_normal((3, 16, 3))

    with pytest.raises(ValueError, match=f"degree {degree} implies"):
        rotate_sh(_rand_rotations(3, 16), c, degree=degree)
