#!/usr/bin/env python3
"""
run_penguin.py — end-to-end CPU driver: deform a real 3DGS .ply with ARAP.

Glue only, no new algorithms:

    read_ply → knn_edges → build_graph → make_anchors → arap_solve
             → carry_gaussian → write_ply

Example (bend the penguin's head, feet pinned):

    python run_penguin.py \
        --ply data/penguin_original.ply --out outputs/penguin_bent.ply \
        --k 12 --gamma 50 \
        --fixed-box  -0.25 -0.25 -0.25   0.35 -0.10 0.15 \
        --handle-box -0.25  0.25 -0.25   0.35  0.40 0.15 \
        --disp 0.05 0.0 0.0

Zero displacement (--disp 0 0 0) is the identity check: the output must be
visually identical to the input — it guards the whole read→carry→write chain.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import replace

import numpy as np

from arap_core import (
    arap_solve,
    assert_connected,
    build_graph,
    carry_gaussian,
    knn_edges,
    make_rbf_weight_fn,
    read_ply,
    write_ply,
)
from arap_core.select import make_anchors, select_box


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Deform a 3DGS .ply with the validated ARAP core (CPU)."
    )
    p.add_argument("--ply", required=True, help="input 3DGS .ply")
    p.add_argument("--out", required=True, help="output .ply path")
    p.add_argument("--k", type=int, default=12,
                   help="kNN connectivity (graph knob, NOT the weight-sweep K)")
    p.add_argument("--gamma", type=float, default=50.0,
                   help="RBF weight decay (the scope knob)")
    p.add_argument("--handle-box", type=float, nargs=6, required=True,
                   metavar=("LX", "LY", "LZ", "HX", "HY", "HZ"),
                   help="axis-aligned box of the MOVING region")
    p.add_argument("--fixed-box", type=float, nargs=6, default=None,
                   metavar=("LX", "LY", "LZ", "HX", "HY", "HZ"),
                   help="axis-aligned box of the PINNED region")
    p.add_argument("--disp", type=float, nargs=3, required=True,
                   metavar=("DX", "DY", "DZ"),
                   help="displacement applied to the handle box")
    p.add_argument("--max-iters", type=int, default=100)
    p.add_argument("--tol", type=float, default=1e-4)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    t_start = time.time()

    # 1. Read the asset -----------------------------------------------------
    t0 = time.time()
    cloud = read_ply(args.ply)
    print(f"[read ]  {cloud.n_gaussians} Gaussians, SH degree {cloud.sh_degree} "
          f"({time.time() - t0:.2f}s)")

    # 2. Connectivity -------------------------------------------------------
    t0 = time.time()
    edges = knn_edges(cloud.xyz, args.k)
    n_comp = assert_connected(cloud.n_gaussians, edges)
    print(f"[graph]  k={args.k}: {len(edges)} edges, "
          f"{n_comp} component(s) ({time.time() - t0:.2f}s)")
    if n_comp > 1:
        print("         *** WARNING: disconnected graph — islands will not "
              "follow the deformation. Increase --k. ***")

    # 3. Build the ARAP graph ------------------------------------------------
    t0 = time.time()
    graph = build_graph(cloud.xyz, edges, make_rbf_weight_fn(gamma=args.gamma))
    print(f"[graph]  Laplacian assembled, gamma={args.gamma} "
          f"({time.time() - t0:.2f}s)")

    # 4. Anchors -------------------------------------------------------------
    moving = select_box(cloud.xyz, args.handle_box[:3], args.handle_box[3:])
    if args.fixed_box is not None:
        fixed = select_box(cloud.xyz, args.fixed_box[:3], args.fixed_box[3:])
    else:
        fixed = None
    anchors = make_anchors(cloud.xyz, moving, np.array(args.disp),
                           fixed_idx=fixed)
    print(f"[edit ]  {len(moving)} moving + "
          f"{0 if fixed is None else len(fixed)} fixed "
          f"= {len(anchors.indices)} anchors, disp {args.disp}")

    # 5. Solve ---------------------------------------------------------------
    t0 = time.time()
    result = arap_solve(graph, anchors, max_iters=args.max_iters, tol=args.tol)
    t_solve = time.time() - t0
    e = result.energy_trace
    rises = np.diff(e)
    assert np.all(rises <= 1e-9 * max(1.0, e[0])), (
        f"ENERGY ROSE at iter {int(np.argmax(rises)) + 1} — solver bug on "
        f"real data"
    )
    print(f"[solve]  {result.n_iters} iters, converged={result.converged}, "
          f"energy {e[0]:.6f} → {e[-1]:.6f} (monotone ✓) ({t_solve:.2f}s)")

    # 6. Carry the Gaussians -------------------------------------------------
    t0 = time.time()
    quats2, scales2 = carry_gaussian(result.rotations, cloud.quats,
                                     cloud.scales)
    cloud2 = replace(cloud, xyz=result.positions, quats=quats2,
                     scales=scales2)
    print(f"[carry]  rotation fast path, scales unchanged "
          f"({time.time() - t0:.2f}s)")
    # This demo carries position, rotation and scale only. `arap_core.gaussian`
    # DOES implement real Wigner-D SH rotation (`rotate_sh`, degrees 0-3, 6
    # tests); this script simply does not wire it in, because the identity check
    # it exists for is exact without it — band 0 is rotation-invariant. Saying
    # "DC-only stub" here, as this line did until 2026-08-06, asserted a library
    # limitation that has not existed since B1. See evidence/PROVENANCE.toml.
    print("         SH view-dependent bands not carried by this demo "
          "(arap_core.rotate_sh implements them; not wired in here).")

    # 7. Write ---------------------------------------------------------------
    t0 = time.time()
    write_ply(cloud2, args.out)
    print(f"[write]  {args.out} ({time.time() - t0:.2f}s)")

    # 8. Summary ---------------------------------------------------------------
    print(f"\nTotal: {time.time() - t_start:.2f}s  |  "
          f"N={cloud.n_gaussians}  E={len(edges)}  comps={n_comp}  "
          f"iters={result.n_iters}  converged={result.converged}")


if __name__ == "__main__":
    main()
