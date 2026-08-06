"""
refs.py — independent reference implementations + synthetic geometry for the
ARAP core diagnostic. READ-ONLY w.r.t. arap_core: nothing here is imported by
the core, and the core is never patched.

Everything is re-derived from the textbook ARAP definitions so the Phase-2
cross-checks do not depend on the core's own assembly/factorisation/vectorised
SVD. Synthetic weight functions are built here (not from the probe) so that
"does the core consume weights" is tested independently of the probe's RBF.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve


# --------------------------------------------------------------------------- #
# Synthetic geometry
# --------------------------------------------------------------------------- #
def chain(n=41, h=1.0, axis=0):
    """Straight chain of n uniformly spaced nodes; path edges (i, i+1)."""
    X = np.zeros((n, 3))
    X[:, axis] = np.arange(n) * h
    edges = np.column_stack([np.arange(n - 1), np.arange(1, n)]).astype(np.int64)
    return X, edges


def grid(nx, ny, nz, h=1.0):
    """3D grid of points with 6-connectivity (axis-adjacent) edges.

    Deterministic and mirror-symmetric — used for the bar / symmetry cases.
    Returns (positions (N,3), edges (E,2) i<j, idx lookup (nx,ny,nz)->vertex).
    """
    idx = np.arange(nx * ny * nz).reshape(nx, ny, nz)
    xs, ys, zs = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    X = np.column_stack([xs.ravel(), ys.ravel(), zs.ravel()]).astype(np.float64) * h
    E = []
    for a in range(nx):
        for b in range(ny):
            for c in range(nz):
                v = idx[a, b, c]
                if a + 1 < nx: E.append((v, idx[a + 1, b, c]))
                if b + 1 < ny: E.append((v, idx[a, b + 1, c]))
                if c + 1 < nz: E.append((v, idx[a, b, c + 1]))
    edges = np.array([(min(i, j), max(i, j)) for i, j in E], dtype=np.int64)
    edges = np.unique(edges, axis=0)
    return X, edges, idx


def scene_scale(X):
    """Bounding-box diagonal — the natural length unit for ε perturbations."""
    return float(np.linalg.norm(X.max(0) - X.min(0)))


# --------------------------------------------------------------------------- #
# Synthetic weight functions (independent of the probe)
# --------------------------------------------------------------------------- #
def w_uniform(positions, edges):
    """Maximally flat: every w_ij = 1."""
    return np.ones(len(edges), dtype=np.float64)


def w_delta(positions, edges, eps=1e-6):
    """Maximally local: keep the *nearest* incident edge of each endpoint at
    weight 1, drive every other edge to eps."""
    d = np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)
    w = np.full(len(edges), eps, dtype=np.float64)
    N = int(edges.max()) + 1
    for v in range(N):
        inc = np.where((edges[:, 0] == v) | (edges[:, 1] == v))[0]
        if inc.size:
            w[inc[np.argmin(d[inc])]] = 1.0
    return w


def w_broad(positions, edges):
    """Deliberately wide, clearly-varying kernel: grows with edge length."""
    d = np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)
    dm = d.mean() if d.mean() > 0 else 1.0
    return (d / dm) ** 2 + 0.1


def w_rbf(gamma):
    """Independent RBF (NOT the probe's scale-normalised one)."""
    def f(positions, edges):
        d = positions[edges[:, 0]] - positions[edges[:, 1]]
        return np.exp(-gamma * np.einsum("ij,ij->i", d, d))
    return f


# --------------------------------------------------------------------------- #
# Independent reference ARAP pieces (textbook, naive-but-trustworthy)
# --------------------------------------------------------------------------- #
def ref_energy(rest, defo, R, edges, w):
    """E = Σ_i Σ_{j∈N(i)} w_ij ‖(p'_i−p'_j) − R_i(p_i−p_j)‖².

    Undirected edge (i,j) contributes to i's cell (R_i) and j's cell (R_j).
    Standalone — does not call arap_core.
    """
    i, j = edges[:, 0], edges[:, 1]
    d = rest[i] - rest[j]
    dp = defo[i] - defo[j]
    Ri = np.einsum("eab,eb->ea", R[i], d)
    Rj = np.einsum("eab,eb->ea", R[j], d)
    si = np.einsum("ea,ea->e", dp - Ri, dp - Ri)
    sj = np.einsum("ea,ea->e", dp - Rj, dp - Rj)
    return float(np.sum(w * (si + sj)))


def ref_fit_rotations(rest, defo, edges, w, N):
    """Independent weighted-Procrustes rotation fit, matching the core's
    S = Σ w (p_i−p_j)(p'_i−p'_j)ᵀ, R = V Uᵀ, det-corrected convention."""
    i, j = edges[:, 0], edges[:, 1]
    d = rest[i] - rest[j]
    dp = defo[i] - defo[j]
    outer = (w[:, None] * d)[:, :, None] * dp[:, None, :]
    S = np.zeros((N, 3, 3))
    np.add.at(S, i, outer)
    np.add.at(S, j, outer)
    R = np.empty((N, 3, 3))
    for k in range(N):
        U, s, Vt = np.linalg.svd(S[k])
        Rk = Vt.T @ U.T
        if np.linalg.det(Rk) < 0:
            Vf = Vt.T.copy()
            Vf[:, np.argmin(s)] *= -1
            Rk = Vf @ U.T
        if s.max() < 1e-14:
            Rk = np.eye(3)
        R[k] = Rk
    return R


def ref_L(N, edges, w):
    """Independent L = D − W assembly."""
    i, j = edges[:, 0], edges[:, 1]
    rows = np.concatenate([i, j, i, j])
    cols = np.concatenate([j, i, i, j])
    data = np.concatenate([-w, -w, w, w])
    return sp.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()


def ref_rhs(rest, R, edges, w, N):
    """Independent Sorkine–Alexa RHS b_i = Σ_j w_ij ½(R_i+R_j)(p_i−p_j)."""
    i, j = edges[:, 0], edges[:, 1]
    d = rest[i] - rest[j]
    Ravg = 0.5 * (R[i] + R[j])
    contrib = w[:, None] * np.einsum("eab,eb->ea", Ravg, d)
    b = np.zeros((N, 3))
    np.add.at(b, i, contrib)
    np.add.at(b, j, -contrib)
    return b


def ref_solve_positions(rest, R, edges, w, anc_idx, anc_tgt):
    """Independent hard-constrained single global solve for a *fixed* R, using a
    fresh direct solver (spsolve). Used by the Phase-2.2 position cross-check and
    the Phase-5 N1 prefactor-vs-direct check."""
    N = rest.shape[0]
    L = ref_L(N, edges, w).tolil()
    for a in anc_idx:
        L[a, :] = 0.0
        L[a, a] = 1.0
    Lc = L.tocsc()
    b = ref_rhs(rest, R, edges, w, N)
    b[anc_idx] = anc_tgt
    return np.column_stack([spsolve(Lc, b[:, c]) for c in range(3)])


def ref_arap(rest, edges, w, anc_idx, anc_tgt, max_iters=6000, tol=1e-12, init=None):
    """Fully independent ARAP alternation (own local + global steps, own direct
    solve). Gold reference for the cantilever / cross-checks."""
    N = rest.shape[0]
    L = ref_L(N, edges, w).tolil()
    for a in anc_idx:
        L[a, :] = 0.0
        L[a, a] = 1.0
    Lc = L.tocsc()
    if init is not None:
        p = np.array(init, float)
    else:
        p = rest.copy()
        p[anc_idx] = anc_tgt
    R = np.tile(np.eye(3), (N, 1, 1))
    trace = []
    for it in range(max_iters):
        R = ref_fit_rotations(rest, p, edges, w, N)
        b = ref_rhs(rest, R, edges, w, N)
        b[anc_idx] = anc_tgt
        p_new = np.column_stack([spsolve(Lc, b[:, c]) for c in range(3)])
        trace.append(ref_energy(rest, p_new, R, edges, w))
        delta = np.linalg.norm(p_new - p, axis=1).max()
        p = p_new
        if delta < tol:
            break
    return p, R, np.array(trace), it + 1
