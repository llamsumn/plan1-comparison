"""Seam-2 tests for the Gaussian carry — both paths, and the branches inside them.

`carry_gaussian` has two implementations behind one signature. The rotation path
composes quaternions and leaves scales alone; the affine path reconstructs Σ,
transforms it, and eigendecomposes back. The second is the one with the numerics
in it, and two of its branches had never run.

**The reflection guard.** `np.linalg.eigh` returns an orthonormal eigenvector
matrix with no promise about its determinant, so it is a rotation half the time
and a reflection the other half. A reflection stored as a quaternion is not a
reflection — the conversion silently produces the nearest rotation — so the
Gaussian would come back mirrored. The guard flips a column when the determinant
is negative; both sides of it are exercised here, because a guard that has only
ever been seen firing has not been shown to leave correct input alone.

**Shepperd's branch selection.** `_R_to_quat` picks among four formulas by
largest denominator. The trace branch is chosen for most rotations, and the
suite's random inputs took it every time. The other three exist for rotations
near 180°, which is precisely where the trace branch loses its precision, so they
are the numerically interesting ones and they are pinned at exactly 180°.
"""

import numpy as np
import pytest

from arap_core.gaussian import (
    _quat_to_R,
    _R_to_quat,
    carry_gaussian,
    extract_quaternion_scale,
    transform_covariances,
)

IDENTITY_QUAT = np.array([[1.0, 0.0, 0.0, 0.0]])

#: Ascending axis lengths, so the covariance they build has ascending eigenvalues
#: and `eigh` returns them in the order it found them — a proper rotation, which
#: is the case the reflection guard must leave alone.
ASCENDING_SCALES = np.array([[1.0, 2.0, 3.0]])

#: The same three lengths the other way round. `eigh` sorts ascending regardless,
#: so recovering them means permuting the eigenvectors, and an odd permutation is
#: a reflection — the case the guard exists for.
DESCENDING_SCALES = np.array([[3.0, 2.0, 1.0]])


def identity(n):
    return np.tile(np.eye(3), (n, 1, 1))


# ── the reflection guard, both ways ─────────────────────────────────────────
@pytest.mark.parametrize(
    "scales", [ASCENDING_SCALES, DESCENDING_SCALES], ids=["no-flip", "flip"]
)
def test_the_affine_path_recovers_the_covariance_it_was_given(scales):
    """The shape that went in is the shape that comes back.

    **`det(R) == +1` is the obvious assertion here and it is worthless**, which
    is worth writing down because it took a deliberate break to notice. A
    quaternion cannot represent a reflection: `_R_to_quat` of an improper matrix
    silently returns the nearest proper rotation, so the determinant of anything
    that has been through the quaternion round trip is +1 whether the guard ran
    or not. The test passed with the flip deleted.

    What the guard actually protects is the *identity* of the rotation, not its
    properness. Skip it and `_R_to_quat` is handed a reflection, quietly
    substitutes a different rotation, and the Gaussian comes back with the wrong
    orientation — reconstructing Σ from the returned pair is off by 8.0 on this
    input rather than by 1e-15. So Σ is what gets asserted.
    """
    quats, out_scales = carry_gaussian(
        identity(1), IDENTITY_QUAT, scales, jacobians=identity(1)
    )

    given = np.einsum("nij,nj,nkj->nik", identity(1), scales**2, identity(1))
    recovered_frame = _quat_to_R(quats)
    recovered = np.einsum(
        "nij,nj,nkj->nik", recovered_frame, out_scales**2, recovered_frame
    )

    np.testing.assert_allclose(recovered, given, atol=1e-12)
    np.testing.assert_allclose(np.sort(out_scales[0]), np.sort(scales[0]), atol=1e-12)


@pytest.mark.parametrize(
    "scales, expected_det",
    [(ASCENDING_SCALES, 1.0), (DESCENDING_SCALES, -1.0)],
    ids=["eigh-gives-a-rotation", "eigh-gives-a-reflection"],
)
def test_the_two_fixtures_really_do_land_on_opposite_sides_of_the_guard(
    scales, expected_det
):
    """The control for the pair above. Both cases pass the `det == +1` assertion,
    so on their own they cannot show that the guard was reached in one and not
    the other — this asserts the input condition directly, and would fail if a
    future NumPy changed `eigh`'s sign convention and quietly collapsed the two
    cases into one."""
    covariance = np.einsum(
        "nij,nj,nkj->nik", identity(1), scales**2, identity(1)
    )
    _, eigvecs = np.linalg.eigh(covariance)
    assert np.linalg.det(eigvecs)[0] == pytest.approx(expected_det)


def test_the_affine_path_recovers_the_shape_it_was_given():
    """An identity Jacobian is the identity deformation, so Σ comes back
    unchanged and the axis lengths are the ones that went in. This is what says
    the eigendecomposition round-trip is faithful rather than merely proper."""
    quats, scales = carry_gaussian(
        identity(1), IDENTITY_QUAT, ASCENDING_SCALES, jacobians=identity(1)
    )
    np.testing.assert_allclose(scales, ASCENDING_SCALES, atol=1e-12)
    np.testing.assert_allclose(np.abs(quats[0]), np.array([1.0, 0.0, 0.0, 0.0]), atol=1e-12)


def test_the_rotation_path_leaves_the_scales_untouched():
    """The documented difference between the two paths, and the reason the cheap
    one is the default: a rotation cannot change an axis length, so there is
    nothing to recompute."""
    scales = np.array([[1.0, 2.0, 3.0], [0.5, 0.5, 4.0]])
    quats = np.tile(IDENTITY_QUAT, (2, 1))

    _, out = carry_gaussian(identity(2), quats, scales)

    np.testing.assert_array_equal(out, scales)
    assert out is not scales, "the caller's array must not be aliased"


def test_a_negative_eigenvalue_is_clamped_rather_than_producing_a_nan():
    """Σ is PSD in exact arithmetic and can come back a hair negative in floating
    point. `sqrt` of a negative is NaN, which would travel into the written file,
    so the clamp is what keeps a rounding error from becoming a corrupt asset."""
    almost_psd = np.diag([-1e-18, 1.0, 4.0])[np.newaxis]

    _, scales = extract_quaternion_scale(almost_psd)

    assert np.all(np.isfinite(scales))
    assert scales[0, 0] == 0.0


# ── Shepperd's four branches ────────────────────────────────────────────────
#: 180° about each axis. Trace is −1 for all three, which is the smallest of the
#: four denominators, so none of them takes the trace branch.
HALF_TURNS = np.array(
    [
        [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]],
        [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]],
        [[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
    ]
)


def test_half_turns_round_trip_through_the_non_trace_branches():
    """The three branches the trace formula exists to avoid. At exactly 180° the
    trace denominator is zero, so taking that branch would divide by zero — this
    passing is the evidence that the selection works, not just that the formulas
    do."""
    quats = _R_to_quat(HALF_TURNS)

    np.testing.assert_allclose(_quat_to_R(quats), HALF_TURNS, atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(quats, axis=1), 1.0, atol=1e-12)


def test_a_small_rotation_still_takes_the_trace_branch():
    """The negative control. Without it the test above is consistent with a
    `_R_to_quat` that had lost the trace branch entirely."""
    theta = 0.05
    small = np.array(
        [
            [
                [np.cos(theta), -np.sin(theta), 0.0],
                [np.sin(theta), np.cos(theta), 0.0],
                [0.0, 0.0, 1.0],
            ]
        ]
    )
    quats = _R_to_quat(small)

    assert quats[0, 0] == pytest.approx(np.cos(theta / 2), abs=1e-12)
    np.testing.assert_allclose(_quat_to_R(quats), small, atol=1e-12)


def test_transform_covariances_defaults_to_the_rotation_when_no_jacobian_is_given():
    """The documented default, and the one line of `transform_covariances` that
    chooses between its two arguments."""
    covariance = np.diag([1.0, 4.0, 9.0])[np.newaxis]
    rotation = HALF_TURNS[:1]

    with_default = transform_covariances(rotation, covariance)
    with_explicit = transform_covariances(rotation, covariance, jacobians=rotation)

    np.testing.assert_array_equal(with_default, with_explicit)
