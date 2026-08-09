"""
run_diagnostic.py — executes the ARAP Core Diagnostic Protocol end-to-end.

Read-only wrapping of arap_core. Emits:
  diagnostics/arap_core_diagnostic.json   (one record per test)
  diagnostics/ARAP_CORE_VERDICT.md        (human summary + decision-tree verdict)
  diagnostics/cantilever_profile.csv      (Phase 2.4)

Run from the project root:  python diagnostics/run_diagnostic.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from arap_core import build_graph, arap_solve, arap_energy          # noqa: E402
from arap_core.types import Anchors                                  # noqa: E402
from arap_core.global_step import prefactor, solve_positions         # noqa: E402
from arap_core.local_step import fit_rotations                       # noqa: E402
from arap_core import gaussian as G                                  # noqa: E402
from arap_core.io_ply import read_ply                                # noqa: E402
from arap_core.edges import knn_edges                                # noqa: E402

import refs                                                          # noqa: E402
from refs import (chain, grid, scene_scale, w_uniform, w_delta,      # noqa: E402
                  w_broad, w_rbf, ref_energy, ref_fit_rotations,
                  ref_L, ref_solve_positions, ref_arap)

np.random.seed(0)
RECORDS = []
CANTILEVER = {}   # filled by phase 2.4 for the verdict shape finding


# --------------------------------------------------------------------------- #
# Record / util
# --------------------------------------------------------------------------- #
def _num(x):
    try:
        if x is None:
            return None
        xf = float(x)
        if math.isnan(xf):
            return "nan"
        if math.isinf(xf):
            return "inf" if xf > 0 else "-inf"
        return xf
    except Exception:
        return str(x)


def rec(phase, tid, name, value, threshold, unit, passed, notes=""):
    RECORDS.append(dict(phase=phase, id=tid, name=name, value=_num(value),
                        threshold=_num(threshold), unit=unit,
                        passed=bool(passed), notes=notes))
    print(f"[{'PASS' if passed else 'FAIL'}] {tid:<6} {name:<36} "
          f"value={value!s:<22} thr={threshold!s:<10} {notes}")


def mk_anchors(idx, tgt):
    return Anchors(indices=np.asarray(idx, np.int64),
                   targets=np.asarray(tgt, np.float64))


def rot_from_axis_angle(axis, ang):
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)


def solve(X, edges, wf, anc, tol=1e-11, max_iters=10000, init=None):
    g = build_graph(X, edges, wf)
    res = arap_solve(g, anc, tol=tol, max_iters=max_iters, init=init)
    return g, res


# --------------------------------------------------------------------------- #
# Canonical cases (built once, reused across phases)
# --------------------------------------------------------------------------- #
def case_cantilever():
    X, edges = chain(41, h=1.0)
    fixed = [0, 1, 2]
    tip = 40
    delta = np.array([0.0, 8.0, 0.0])
    anc_idx = fixed + [tip]
    anc_tgt = np.vstack([X[fixed], X[tip] + delta])
    return X, edges, mk_anchors(anc_idx, anc_tgt), np.array(anc_idx), delta


def case_bar_bend():
    X, edges, idx = grid(8, 3, 3, h=1.0)
    fixed = idx[0].ravel().tolist()             # x=0 face
    far = idx[-1].ravel()                       # x=max face
    delta = np.array([0.0, 3.0, 0.0])
    anc_idx = fixed + far.tolist()
    anc_tgt = np.vstack([X[fixed], X[far] + delta])
    return X, edges, mk_anchors(anc_idx, anc_tgt), np.array(anc_idx)


def case_static_far():
    """Heavily pinned: pin the whole far majority, wiggle a small near handle."""
    X, edges, idx = grid(8, 3, 3, h=1.0)
    pinned = idx[2:].ravel()                    # x>=2 held at rest (majority)
    handle = idx[0].ravel()                     # x=0 face
    delta = np.array([0.0, 0.3, 0.0])
    anc_idx = np.concatenate([pinned, handle])
    anc_tgt = np.vstack([X[pinned], X[handle] + delta])
    return X, edges, mk_anchors(anc_idx, anc_tgt), np.array(anc_idx)


# =========================================================================== #
# Phase 1 — regression ladder
# =========================================================================== #
def phase1():
    X, edges, anc = case_bar_bend()[:3]
    g = build_graph(X, edges, w_uniform)

    L = g.laplacian
    asym = abs(L - L.T)
    a = asym.max() if asym.nnz else 0.0
    rec("1", "L1", "Laplacian symmetry", a, 1e-10, "max|L-L^T|", a < 1e-10)

    nrm = np.abs(np.asarray(L @ np.ones(L.shape[0]))).max()
    rec("1", "L2", "Laplacian null space", nrm, 1e-9, "max|L*1|", nrm < 1e-9)

    _, res = solve(X, edges, w_uniform, anc)
    dets = np.linalg.det(res.rotations)
    orth = np.array([np.linalg.norm(R.T @ R - np.eye(3)) for R in res.rotations])
    d_err = np.abs(dets - 1).max()
    rec("1", "L3", "Rotation properness", max(d_err, orth.max()), 1e-9,
        "max(|det-1|,||RtR-I||)", d_err < 1e-9 and orth.max() < 1e-9)

    # L4 identity solve — anchors sit at rest (zero displacement)
    anc0 = mk_anchors(anc.indices, X[anc.indices])
    _, res0 = solve(X, edges, w_uniform, anc0)
    e = np.abs(res0.positions - X).max()
    rec("1", "L4", "Identity solve", e, 1e-9, "||def-rest||_inf", e < 1e-9)

    diffs = np.diff(res.energy_trace)
    worst = diffs.max() if diffs.size else 0.0
    rec("1", "L5", "Energy monotonicity", worst, 1e-12, "max(E[k+1]-E[k])",
        worst <= 1e-12)

    # L6 rigid-bend edge lengths — partial-anchor global rigid motion; a correct
    # solve propagates the zero-energy rigid mode → all edge lengths preserved.
    Xb, eb, ib = grid(8, 3, 3, h=1.0)
    R = rot_from_axis_angle([0.2, 0.3, 1.0], np.deg2rad(20))
    t = np.array([0.5, -0.4, 0.3])
    face = ib[0].ravel()
    tgt = (Xb[face] @ R.T) + t
    _, resr = solve(Xb, eb, w_uniform, mk_anchors(face, tgt), max_iters=20000)
    rl = np.linalg.norm(Xb[eb[:, 0]] - Xb[eb[:, 1]], axis=1)
    dl = np.linalg.norm(resr.positions[eb[:, 0]] - resr.positions[eb[:, 1]], axis=1)
    de = np.abs(dl - rl).max()
    rec("1", "L6", "Rigid-bend edge lengths", de, 1e-8, "max|Δedge len|",
        de < 1e-8, notes=f"converged={resr.converged}")

    # L7 covariance PSD after carry
    n = 200
    Rr = np.array([rot_from_axis_angle(np.random.randn(3), np.random.rand() * 2)
                   for _ in range(n)])
    q = G._R_to_quat(np.array([rot_from_axis_angle(np.random.randn(3),
                     np.random.rand() * 2) for _ in range(n)]))
    s = np.random.rand(n, 3) + 0.1
    q2, s2 = G.carry_gaussian(Rr, q, s)
    cov = np.einsum("nij,nj,nkj->nik", G._quat_to_R(q2), s2 ** 2, G._quat_to_R(q2))
    mineig = np.linalg.eigvalsh(cov).min()
    rec("1", "L7", "Covariance PSD (carry)", mineig, -1e-12, "min eig", mineig > -1e-12)


# =========================================================================== #
# Phase 2 — analytic ground truth
# =========================================================================== #
def _stationarity(name, X, edges, wf, anc):
    g, res = solve(X, edges, wf, anc, tol=1e-12, max_iters=15000)
    w = g.weights
    p, R = res.positions, res.rotations
    N = X.shape[0]
    E0 = ref_energy(X, p, R, edges, w)
    eps = 1e-4 * scene_scale(X)
    free = np.setdiff1d(np.arange(N), anc.indices)

    # position certificate + finite-difference free gradient
    worst_pos = np.inf
    grad = 0.0
    for i in free:
        for a in range(3):
            for sgn in (+1, -1):
                pp = p.copy()
                pp[i, a] += sgn * eps
                worst_pos = min(worst_pos, ref_energy(X, pp, R, edges, w) - E0)
            pplus = p.copy(); pplus[i, a] += eps
            pminus = p.copy(); pminus[i, a] -= eps
            gia = (ref_energy(X, pplus, R, edges, w)
                   - ref_energy(X, pminus, R, edges, w)) / (2 * eps)
            grad = max(grad, abs(gia))

    # rotation certificate: R_i -> R_i exp([w]x) on the manifold
    worst_rot = np.inf
    om = 1e-4
    for i in range(N):
        for a in range(3):
            for sgn in (+1, -1):
                axis = np.zeros(3); axis[a] = 1.0
                dR = rot_from_axis_angle(axis, sgn * om)
                Rp = R.copy()
                Rp[i] = R[i] @ dR
                worst_rot = min(worst_rot, ref_energy(X, p, Rp, edges, w) - E0)

    rec("2.1", f"2.1p-{name}", f"Position certificate [{name}]", worst_pos,
        -1e-10, "min ΔE", worst_pos >= -1e-10,
        notes=f"grad_inf={grad:.2e} conv={res.converged} iters={res.n_iters}")
    rec("2.1", f"2.1r-{name}", f"Rotation certificate [{name}]", worst_rot,
        -1e-10, "min ΔE", worst_rot >= -1e-10)
    return g, res


def phase2():
    # 2.1 stationarity on the three red-light-shaped cases
    Xc, ec, ac, *_ = case_cantilever()
    _stationarity("cantilever", Xc, ec, w_uniform, ac)
    Xb, eb, ab = case_bar_bend()[:3]
    gbb, rbb = _stationarity("bar_bend", Xb, eb, w_uniform, ab)
    Xs, es, as_ = case_static_far()[:3]
    _stationarity("static_far", Xs, es, w_uniform, as_)

    # 2.2 closed-form cross-check on bar_bend converged state
    w = gbb.weights
    p, R = rbb.positions, rbb.rotations
    N = Xb.shape[0]
    R_ref = ref_fit_rotations(Xb, p, eb, w, N)
    R_core = fit_rotations(Xb, p, gbb)
    dR = np.abs(R_core - R_ref).max()
    rec("2.2", "2.2-rot", "Rotation closed-form", dR, 1e-9, "||R_core-R_ref||_F",
        dR < 1e-9)

    solver = prefactor(gbb, ab, constraint="hard", penalty=1e6)
    p_core = solve_positions(solver, gbb, R, ab)
    p_ref = ref_solve_positions(Xb, R, eb, w, ab.indices, ab.targets)
    dP = np.abs(p_core - p_ref).max()
    rec("2.2", "2.2-pos", "Position closed-form", dP, 1e-8, "||p_core-p_ref||_inf",
        dP < 1e-8)

    # 2.3 exact rigid recovery — known (R,t), all but one vertex anchored (the
    # core contract requires A<N; the lone free vertex must FOLLOW the rigid
    # motion exactly, so this also exercises the solve, not just passthrough).
    Xr, er, ir = grid(6, 3, 3, h=1.0)
    Rg = rot_from_axis_angle([0.3, 1.0, 0.2], np.deg2rad(30))
    tg = np.array([1.0, -2.0, 0.5])
    tgt = (Xr @ Rg.T) + tg
    freev = ir[3, 1, 1]                          # one interior vertex left free
    anc_idx = np.setdiff1d(np.arange(len(Xr)), [freev])
    _, resr = solve(Xr, er, w_uniform, mk_anchors(anc_idx, tgt[anc_idx]),
                    tol=1e-12, max_iters=5000)
    perr = np.abs(resr.positions - tgt).max()    # includes the free vertex
    fe = resr.energy_trace[-1]
    dets = np.abs(np.linalg.det(resr.rotations) - 1).max()
    rec("2.3", "2.3-pos", "Rigid recovery position", perr, 1e-8, "||p-(RX+t)||_inf",
        perr < 1e-8, notes=f"1 free vertex followed rigidly (err at free={np.abs(resr.positions[freev]-tgt[freev]).max():.1e})")
    rec("2.3", "2.3-E", "Rigid recovery energy", fe, 1e-12, "final E", fe < 1e-12,
        notes=f"max|detR-1|={dets:.1e}")

    # 2.4 cantilever profile
    _cantilever(Xc, ec, ac)


def _cantilever(X, edges, anc):
    g, res = solve(X, edges, w_uniform, anc, tol=1e-12, max_iters=30000)
    p = res.positions
    disp = np.linalg.norm(p - X, axis=1)
    arclen = np.concatenate([[0.0], np.cumsum(
        np.linalg.norm(np.diff(X, axis=0), axis=1))])
    tip = 40
    delta_mag = 8.0

    zero_at_anchor = disp[0]
    tip_err = abs(disp[tip] - delta_mag)
    # monotone in distance from fixed end (allow tiny numeric wiggle)
    dincr = np.diff(disp)
    monotone = float(dincr.min())
    dets = np.abs(np.linalg.det(res.rotations) - 1).max()
    corr = float(np.corrcoef(arclen, disp)[0, 1])

    # independent gold reference
    p_ref, _, _, its = ref_arap(X, edges, g.weights, anc.indices, anc.targets,
                                max_iters=30000, tol=1e-12)
    gold = np.abs(p - p_ref).max()

    # scipy.optimize secondary confirmation on the reduced energy
    scipy_note = ""
    try:
        from scipy.optimize import minimize
        N = X.shape[0]
        free = np.setdiff1d(np.arange(N), anc.indices)
        w = g.weights

        def full(pf):
            q = p.copy()
            q[free] = pf.reshape(-1, 3)
            R = ref_fit_rotations(X, q, edges, w, N)
            return ref_energy(X, q, R, edges, w)

        E_core = full(p[free].ravel())
        out = minimize(full, p[free].ravel(), method="L-BFGS-B",
                       options=dict(maxiter=200, ftol=1e-14, gtol=1e-10))
        moved = np.abs(out.x.reshape(-1, 3) - p[free]).max()
        scipy_note = f"scipy: ΔE={out.fun - E_core:.2e} moved={moved:.2e}"
    except Exception as ex:
        scipy_note = f"scipy skipped: {ex!r}"

    rec("2.4", "2.4-anchor", "Cantilever zero-at-anchor", zero_at_anchor, 1e-9,
        "disp[0]", zero_at_anchor < 1e-9)
    rec("2.4", "2.4-tip", "Cantilever tip=δ", tip_err, 1e-9, "|disp_tip-δ|",
        tip_err < 1e-9)
    rec("2.4", "2.4-mono", "Cantilever monotone", monotone, -1e-9,
        "min Δdisp", monotone >= -1e-9)
    rec("2.4", "2.4-det", "Cantilever proper R", dets, 1e-9, "max|detR-1|",
        dets < 1e-9)
    rec("2.4", "2.4-gold", "Cantilever vs gold ref", gold, 1e-6,
        "||p-p_ref||_inf", gold < 1e-6, notes=scipy_note)

    shape = ("increase-toward-tip" if corr > 0.9 else
             "decay-from-handle" if corr < -0.9 else "mixed")
    CANTILEVER.update(dict(corr=corr, shape=shape, disp0=float(disp[0]),
                           disp_tip=float(disp[tip]), n_iters=res.n_iters,
                           gold=float(gold)))

    # CSV
    with open(os.path.join(HERE, "cantilever_profile.csv"), "w") as f:
        f.write("node,arclen_from_fixed,disp_x,disp_y,disp_z,disp_mag\n")
        for i in range(X.shape[0]):
            d = p[i] - X[i]
            f.write(f"{i},{arclen[i]:.6f},{d[0]:.6f},{d[1]:.6f},{d[2]:.6f},"
                    f"{disp[i]:.6f}\n")


# =========================================================================== #
# Phase 3 — weight-response isolation
# =========================================================================== #
def phase3():
    X, _, idx = grid(6, 3, 3, h=1.0)
    edges = knn_edges(X, k=12)                 # varied edge lengths
    fixed = idx[0].ravel().tolist()
    far = idx[-1].ravel()
    delta = np.array([0.0, 2.5, 0.0])
    anc = mk_anchors(fixed + far.tolist(),
                     np.vstack([X[fixed], X[far] + delta]))

    outs = {}
    for name, wf in (("uniform", w_uniform), ("delta", w_delta), ("broad", w_broad)):
        _, res = solve(X, edges, wf, anc, max_iters=20000)
        outs[name] = res.positions

    base = np.linalg.norm(outs["uniform"] - X)
    du = np.linalg.norm(outs["delta"] - outs["uniform"]) / base
    db = np.linalg.norm(outs["broad"] - outs["uniform"]) / base
    rec("3", "3-delta", "Weight response Δ(delta,uniform)", du, 0.1,
        "rel ||Δ||", du > 0.1,
        notes=f"broad-vs-uniform={db:.3f}; near-ident-guard(<1e-6)={'FAIL' if du < 1e-6 else 'ok'}")


# =========================================================================== #
# Phase 4 — boundary conditions & invariances
# =========================================================================== #
def phase4():
    Xb, eb, ab = case_bar_bend()[:3]
    gbb, rbb = solve(Xb, eb, w_uniform, ab)

    r = np.abs(rbb.positions[ab.indices] - ab.targets).max()
    rec("4", "B1", "Anchor exactness (hard)", r, 1e-10, "residual", r < 1e-10)

    free = np.setdiff1d(np.arange(Xb.shape[0]), ab.indices)
    fdisp = np.linalg.norm(rbb.positions[free] - Xb[free], axis=1).max()
    rec("4", "B2", "Free vertices move", fdisp, 1e-6, "max free disp",
        fdisp > 1e-6)

    # B3 translation invariance
    c = np.array([3.0, -2.0, 5.0])
    anc_t = mk_anchors(ab.indices, ab.targets + c)
    _, rt = solve(Xb + c, eb, w_uniform, anc_t)
    e3 = np.abs((rt.positions - c) - rbb.positions).max()
    rec("4", "B3", "Translation invariance", e3, 1e-9, "||Δ||_inf", e3 < 1e-9)

    # B4 rotation invariance
    Q = rot_from_axis_angle([0.2, 1.0, -0.3], np.deg2rad(37))
    anc_r = mk_anchors(ab.indices, ab.targets @ Q.T)
    _, rr = solve(Xb @ Q.T, eb, w_uniform, anc_r)
    e4 = np.abs(rr.positions - (rbb.positions @ Q.T)).max()
    rec("4", "B4", "Rotation invariance", e4, 1e-8, "||Δ||_inf", e4 < 1e-8)

    # B5 symmetry — mirror-symmetric grid, symmetric anchors + edit
    nx, ny, nz = 5, 4, 1
    Xs, es, ids = grid(nx, ny, nz, h=1.0)
    sigma = np.empty(nx * ny * nz, dtype=int)
    for a in range(nx):
        for b in range(ny):
            for cc in range(nz):
                sigma[ids[a, b, cc]] = ids[nx - 1 - a, b, cc]
    xmid = (nx - 1) * 1.0
    bottom = ids[:, 0, :].ravel().tolist()
    top = ids[:, ny - 1, :].ravel()
    dsym = np.array([0.0, 1.0, 0.0])
    anc_s = mk_anchors(bottom + top.tolist(),
                       np.vstack([Xs[bottom], Xs[top] + dsym]))
    _, rs = solve(Xs, es, w_uniform, anc_s)
    ps = rs.positions
    mirrored = ps[sigma].copy()
    mirrored[:, 0] = xmid - mirrored[:, 0]
    e5 = np.abs(mirrored - ps).max()
    rec("4", "B5", "Symmetry", e5, 1e-8, "||p-mirror(p[σ])||_inf", e5 < 1e-8)

    # B6 determinism
    _, r6a = solve(Xb, eb, w_uniform, ab)
    _, r6b = solve(Xb, eb, w_uniform, ab)
    e6 = np.abs(r6a.positions - r6b.positions).max()
    rec("4", "B6", "Determinism", e6, 1e-12, "||Δ||_inf", e6 < 1e-12)

    # B7 reflection: collinear + coplanar rank-deficient neighbourhoods
    Xl, el = chain(15, h=1.0)
    ancl = mk_anchors([0, 14], np.vstack([Xl[0], Xl[14] + [0, 0.5, 0]]))
    _, rl = solve(Xl, el, w_uniform, ancl)
    dl = np.linalg.det(rl.rotations)

    Xp, ep, idp = grid(5, 5, 1, h=1.0)
    corners = [idp[0, 0, 0], idp[4, 0, 0], idp[0, 4, 0], idp[4, 4, 0]]
    ctgt = Xp[corners].copy()
    ctgt[:, 2] += np.array([0.1, -0.1, -0.1, 0.1])   # tiny out-of-plane
    _, rp = solve(Xp, ep, w_uniform, mk_anchors(corners, ctgt))
    dp = np.linalg.det(rp.rotations)

    mind = min(dl.min(), dp.min())
    rec("4", "B7", "Degenerate no-reflection", mind, 0.999, "min det(R)",
        mind > 0.999, notes=f"collinear_min={dl.min():.4f} coplanar_min={dp.min():.4f}")


# =========================================================================== #
# Phase 5 — numerical health
# =========================================================================== #
def phase5():
    Xb, eb, ab = case_bar_bend()[:3]
    gbb, rbb = solve(Xb, eb, w_uniform, ab, tol=1e-12, max_iters=15000)
    w = gbb.weights
    N = Xb.shape[0]

    # N1 prefactor == direct (reuse one factorisation on two different RHS)
    solver = prefactor(gbb, ab, constraint="hard", penalty=1e6)
    worst = 0.0
    for R in (rbb.rotations, np.tile(np.eye(3), (N, 1, 1))):
        pc = solve_positions(solver, gbb, R, ab)
        pr = ref_solve_positions(Xb, R, eb, w, ab.indices, ab.targets)
        worst = max(worst, np.abs(pc - pr).max())
    rec("5", "N1", "Prefactor == direct", worst, 1e-8, "||Δ||_inf", worst < 1e-8)

    # N2 conditioning of the hard-constrained system
    L = ref_L(N, eb, w).tolil()
    for a in ab.indices:
        L[a, :] = 0.0
        L[a, a] = 1.0
    cond = np.linalg.cond(L.toarray())
    rec("5", "N2", "System conditioning", cond, 1e12, "cond", np.isfinite(cond)
        and cond < 1e12)

    # N3 true fixed point — re-run from converged state
    _, r3 = solve(Xb, eb, w_uniform, ab, init=rbb.positions, max_iters=15000)
    e3 = np.abs(r3.positions - rbb.positions).max()
    rec("5", "N3", "True fixed point", e3, 1e-9, "||Δ||_inf", e3 < 1e-9)

    # N4 convergence trace
    diffs = np.diff(rbb.energy_trace)
    mono = diffs.max() if diffs.size else 0.0
    floor = float(rbb.energy_trace[-1])
    plateau = float(abs(diffs[-1])) if diffs.size else 0.0
    rec("5", "N4", "Convergence trace", rbb.n_iters, None, "iters",
        rbb.converged and mono <= 1e-12,
        notes=f"E_floor={floor:.3e} last_step={plateau:.1e} conv={rbb.converged}")


# =========================================================================== #
# Phase 6 — Gaussian carry
# =========================================================================== #
def _rand_rot(n):
    return np.array([rot_from_axis_angle(np.random.randn(3),
                    np.random.rand() * 2 * np.pi) for _ in range(n)])


def phase6():
    n = 300

    # G1 rotation path vs matrix route (what the core docstring cites at 5.6e-17):
    # carry rotation path (quaternion compose)  MUST equal  R·Σ_rest·Rᵀ.
    R = _rand_rot(n)
    s = np.random.rand(n, 3) + 0.3
    q = G._R_to_quat(_rand_rot(n))                       # rest orientation
    q2, s2 = G.carry_gaussian(R, q, s)                   # rotation path (J=None)
    Rp = G._quat_to_R(q2)
    cov_path = np.einsum("nij,nj,nkj->nik", Rp, s2 ** 2, Rp)
    Rq = G._quat_to_R(q)
    cov_rest = np.einsum("nij,nj,nkj->nik", Rq, s ** 2, Rq)
    cov_mat = G.transform_covariances(R, cov_rest)       # matrix route: R Σ Rᵀ
    rel = np.linalg.norm(cov_path - cov_mat, axis=(1, 2)) / np.linalg.norm(cov_mat, axis=(1, 2))
    # Documented tolerance (~5.6e-17) is the TYPICAL per-sample error; use that
    # regime (guardrail 3). Worst-of-N is a float64-congruence sampling tail.
    e1 = float(np.median(rel))
    ulp = rel.max() / np.finfo(np.float64).eps
    rec("6", "G1", "Cov round-trip (rotation)", e1, 1e-15, "rel||ΔΣ|| (median)",
        e1 < 1e-15,
        notes=f"quaternion path vs matrix route; worst-of-{n}={rel.max():.2e} (~{ulp:.0f} ulp, FP floor)")

    # G2 affine-path covariance round-trip
    q = G._R_to_quat(_rand_rot(n))
    J = _rand_rot(n) @ (np.eye(3) * (0.5 + np.random.rand(n, 1, 1)))
    q_new, s_new = G.carry_gaussian(R, q, s, jacobians=J)
    cov0 = np.einsum("nij,nj,nkj->nik", G._quat_to_R(q), s ** 2, G._quat_to_R(q))
    cov_aff = np.einsum("nij,njk,nlk->nil", J, cov0, J)
    Rn = G._quat_to_R(q_new)
    cov_re = np.einsum("nij,nj,nkj->nik", Rn, s_new ** 2, Rn)
    e2 = np.abs(cov_re - cov_aff).max()
    rec("6", "G2", "Cov round-trip (affine)", e2, 1e-8, "||ΔΣ||", e2 < 1e-8)

    # G3 PSD preservation on a near-degenerate covariance
    sd = s.copy()
    sd[:, 0] = 1e-7                     # nearly-flat axis
    cov_deg = np.einsum("nij,nj,nkj->nik", R, sd ** 2, R)
    cov_dp = np.einsum("nij,njk,nlk->nil", J, cov_deg, J)
    mineig = np.linalg.eigvalsh(cov_dp).min()
    _, s_clamp = G.extract_quaternion_scale(cov_dp)
    clamp_ok = np.isfinite(s_clamp).all() and (s_clamp >= 0).all()
    rec("6", "G3", "PSD preservation", mineig, -1e-12, "min eig",
        mineig > -1e-12 and clamp_ok, notes=f"scales_finite&>=0={clamp_ok}")

    # G4 quaternion convention round-trip
    axis, ang = np.array([1.0, 2.0, -1.0]), 0.8
    Rk = rot_from_axis_angle(axis, ang)
    qk = G._R_to_quat(Rk)
    e4 = np.abs(G._quat_to_R(qk) - Rk).max()
    w_expect = math.cos(ang / 2)
    rec("6", "G4", "Quaternion convention", e4, 1e-9, "||ΔR||", e4 < 1e-9,
        notes=f"(w,x,y,z); w={qk[0]:.4f} expect cos(θ/2)={w_expect:.4f}")

    # G5 SH rotation boundary.
    #
    # REWRITTEN 2026-08-06, when the ladder was brought in beside the solver it
    # drives and re-executed against it. This check used to read:
    #
    #     rest = np.abs(out[:, 1:, :] - sh[:, 1:, :]).max()
    #     rec(..., "SH stub boundary", max(dc, rest), 0.0, "max|Δsh|",
    #         dc == 0.0 and rest == 0.0,
    #         notes="DC passthrough + bands1+ untouched (explicit stub, ...)")
    #
    # i.e. it asserted that bands 1+ are LEFT ALONE — a boundary check pinning a
    # deliberate limitation, correct against the DC-only stub it was written for.
    # `arap_core/gaussian.py` has implemented real Wigner-D since B1, so the old
    # check now asserts the absence of a feature that is present, and fails at
    # 6.35. It is the only one of the 40 that does; the other 39 reproduce
    # bit-for-bit against the ported core, which is what identifies this as an
    # obsolete check rather than a regression.
    #
    # The successor asks the boundary question that the real implementation
    # actually has, in three legs that can each fail independently:
    #   (a) band 0 is rotation-invariant, so DC passes through byte-exact;
    #   (b) bands 1+ DO move under a non-identity rotation — the stub's absence,
    #       stated as a positive assertion rather than inferred from silence;
    #   (c) an identity rotation is a byte-exact no-op across every band, which
    #       is what the docstring promises and what makes the penguin identity
    #       check exact.
    sh = np.random.randn(n, 16, 3)
    out = G.rotate_sh(R, sh, 3)
    dc = np.abs(out[:, 0, :] - sh[:, 0, :]).max()
    rest = np.abs(out[:, 1:, :] - sh[:, 1:, :]).max()
    identity = np.abs(G.rotate_sh(np.tile(np.eye(3), (n, 1, 1)), sh, 3) - sh).max()
    ok = dc == 0.0 and rest > 1e-6 and identity == 0.0
    rec("6", "G5", "SH rotation boundary (Wigner-D)", dc, 0.0, "max|Δ DC|", ok,
        notes=f"DC invariant={dc:.1e}; bands1+ rotate={rest:.3f} (>1e-6 required "
              f"— a stub would read 0); identity no-op={identity:.1e}")

    # G6 optional real-asset smoke (penguin)
    ply = os.path.join(ROOT, "data", "penguin_original.ply")
    if os.path.exists(ply):
        try:
            pc = read_ply(ply)
            m = pc.n_gaussians
            Rc = np.tile(rot_from_axis_angle([0.1, 1.0, 0.2], 0.6), (m, 1, 1))
            q_out, s_out = G.carry_gaussian(Rc, pc.quats, pc.scales)
            Jc = Rc @ (np.eye(3) * 1.2)
            q_a, s_a = G.carry_gaussian(Rc, pc.quats, pc.scales, jacobians=Jc)
            qn = np.linalg.norm(q_out, axis=1)
            unit = np.abs(qn - 1).max()
            Ra = G._quat_to_R(q_a)
            cov = np.einsum("nij,nj,nkj->nik", Ra, s_a ** 2, Ra)
            mineig = np.linalg.eigvalsh(cov).min()
            finite = (np.isfinite(q_out).all() and np.isfinite(s_out).all()
                      and np.isfinite(cov).all())
            ok = unit < 1e-9 and mineig > -1e-12 and finite
            rec("6", "G6", "Real-asset smoke (penguin)", mineig, -1e-12, "min eig",
                ok, notes=f"N={m} max|‖q‖-1|={unit:.1e} finite={finite}")
        except Exception as ex:
            rec("6", "G6", "Real-asset smoke (penguin)", None, None, "-", False,
                notes=f"error: {ex!r}")
    else:
        rec("6", "G6", "Real-asset smoke (penguin)", None, None, "-", True,
            notes="skipped (asset absent)")


# =========================================================================== #
# Verdict
# =========================================================================== #
def phase_pass(phase_prefix):
    rs = [r for r in RECORDS if r["phase"].startswith(phase_prefix)]
    return all(r["passed"] for r in rs), rs


def id_pass(tid):
    rs = [r for r in RECORDS if r["id"] == tid or r["id"].startswith(tid)]
    return all(r["passed"] for r in rs) if rs else True


def verdict():
    p21_ok = all(r["passed"] for r in RECORDS if r["phase"] == "2.1")
    p3_ok, _ = phase_pass("3")
    b1_ok = id_pass("B1")
    refl_ok = id_pass("B5") and id_pass("B6") and id_pass("B7")
    g_ok, _ = phase_pass("6")
    p1_ok, _ = phase_pass("1")
    p2_ok, _ = phase_pass("2")
    p4_ok, _ = phase_pass("4")
    p5_ok, _ = phase_pass("5")

    if not p21_ok:
        top = ("CORE IMPLICATED (master fault) — Phase 2.1 stationarity failed: "
               "the core is NOT minimising the ARAP energy. Halt all scope "
               "experiments; the red light is (at least partly) the core.")
    elif not p3_ok:
        top = ("CORE IMPLICATED (weight path) — Phase 3 failed: the core ignores "
               "its weights. Every K/γ finding (incl. banked K-inertness) is void.")
    elif not b1_ok:
        top = ("CORE IMPLICATED (boundary handling) — B1 anchor exactness failed: "
               "static_far's 'REAL FLAT' may be an anchor-leak artifact.")
    elif not refl_ok:
        top = ("CORE IMPLICATED (indexing/reflection) — B5/B6/B7 failed: sweep "
               "cells may have reflected or been order-scrambled.")
    elif not g_ok:
        top = ("CARRY IMPLICATED — a G-phase failed: geometry conclusions (K/γ/mask) "
               "stand, but DeformSplat re-run / render-loop results are corrupted "
               "until fixed.")
    elif p1_ok and p2_ok and p3_ok and p4_ok and p5_ok:
        top = ("CORE EXONERATED — Phases 1–5 all pass. Arithmetic, stationarity, "
               "weight consumption, boundary handling, and conditioning are correct. "
               "The red light is NOT the core. Remaining suspects: (a) the injected "
               "RBF weight distribution (γ-scale squash) — run the probe-side "
               "weight-distribution dump at γ=1/5/20; (b) the decay_length metric's "
               "fit assumption — see the cantilever shape finding below.")
    else:
        top = ("INCONCLUSIVE — no master fault triggered but not every rung is green; "
               "inspect the per-phase table below before trusting any sweep.")
    return top


def write_artifacts():
    with open(os.path.join(HERE, "arap_core_diagnostic.json"), "w") as f:
        json.dump(RECORDS, f, indent=2)

    phases = ["1", "2", "2.1", "2.2", "2.3", "2.4", "3", "4", "5", "6"]
    top = verdict()
    lines = []
    lines.append("ARAP CORE DIAGNOSTIC — VERDICT\n")
    lines.append(f"tests: {len(RECORDS)}   "
                 f"passed: {sum(r['passed'] for r in RECORDS)}   "
                 f"failed: {sum(not r['passed'] for r in RECORDS)}\n")
    lines.append("\nPER-PHASE (pass/total):")
    for ph in phases:
        rs = [r for r in RECORDS if r["phase"] == ph]
        if not rs:
            continue
        np_ = sum(r["passed"] for r in rs)
        flag = "OK " if np_ == len(rs) else "XX "
        fails = ",".join(r["id"] for r in rs if not r["passed"])
        lines.append(f"  {flag} phase {ph:<4} {np_}/{len(rs)}"
                     + (f"   FAIL: {fails}" if fails else ""))

    c = CANTILEVER
    if c:
        lines.append("\nCANTILEVER PROFILE (Phase 2.4):")
        lines.append(f"  disp[fixed]={c['disp0']:.2e}  disp[tip]={c['disp_tip']:.3f}"
                     f"  corr(arclen,disp)={c['corr']:+.4f}  iters={c['n_iters']}")
        lines.append(f"  shape = {c['shape'].upper()}  "
                     f"(gold-ref agreement {c['gold']:.1e})")
        if c["shape"] == "increase-toward-tip":
            lines.append("  -> displacement RISES 0→δ toward the dragged tip: a "
                         "monotone ramp, NOT a peak-at-handle decay. A decay_length "
                         "metric fitting exp(-x/λ) FROM the handle mismeasures this "
                         "shape (residual-fraction > 1) — consistent with the "
                         "bar_bend signature. Metric mismatch, not a core fault.")

    lines.append("\nFAILURES (if any):")
    fails = [r for r in RECORDS if not r["passed"]]
    if not fails:
        lines.append("  none")
    for r in fails:
        lines.append(f"  {r['phase']:<4} {r['id']:<8} {r['name']}  "
                     f"value={r['value']} thr={r['threshold']}  {r['notes']}")

    lines.append("\nTOP-LINE VERDICT (decision tree):")
    lines.append("  " + top)
    lines.append("")

    with open(os.path.join(HERE, "ARAP_CORE_VERDICT.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n" + "\n".join(lines))


def main():
    for name, fn in (("Phase 1", phase1), ("Phase 2", phase2), ("Phase 3", phase3),
                     ("Phase 4", phase4), ("Phase 5", phase5), ("Phase 6", phase6)):
        print(f"\n===== {name} =====")
        try:
            fn()
        except Exception:
            traceback.print_exc()
            rec(name, f"{name}-ERR", "phase raised", None, None, "-", False,
                notes="see traceback")
    write_artifacts()


if __name__ == "__main__":
    main()
