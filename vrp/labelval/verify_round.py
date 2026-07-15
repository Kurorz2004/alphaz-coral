"""DELIVERABLE 1 — rounding correctness.

A) .sol `Cost NNNNN` == grader_cost(routes in that .sol)?   [proven-optima on our scale]
B) PyVRP's internal distance matrix (each round_func) == grader _dist, elementwise?
C) PyVRP HGS's reported cost == grader_cost(routes HGS returned)?
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (INST_DIR, SOL_DIR, grader_cost, grader_dist, load_sol,
                    load_vrp, solve_hgs)

random.seed(0)
names = sorted(os.listdir(INST_DIR))
names = [n[:-4] for n in names]

# ---- A) proven optima are on the grader's scale -----------------------------
sample_a = random.sample(names, 300)
bad = []
for nm in sample_a:
    dim, cap, coords, dem = load_vrp(os.path.join(INST_DIR, nm + ".vrp"))
    routes, cost_file = load_sol(os.path.join(SOL_DIR, nm + ".sol"))
    recomputed = grader_cost(coords, routes)
    # also validate the .sol itself: all customers once, capacity respected
    visits = sorted(c for r in routes for c in r)
    ok_perm = visits == list(range(1, dim))
    ok_cap = all(sum(dem[c] for c in r) <= cap for r in routes)
    if recomputed != cost_file or not ok_perm or not ok_cap:
        bad.append((nm, cost_file, recomputed, ok_perm, ok_cap))
print(f"[A] .sol Cost == grader_cost(.sol routes): {len(sample_a)-len(bad)}/{len(sample_a)} match")
print(f"[A] mismatches: {bad[:5]}")

# ---- B) round_func vs grader _dist, elementwise over the full 101x101 matrix -
import vrplib
from pyvrp.read import ROUND_FUNCS

sample_b = random.sample(names, 25)
counts = {k: 0 for k in ROUND_FUNCS}
worst = {k: 0 for k in ROUND_FUNCS}
npairs = 0
for nm in sample_b:
    p = os.path.join(INST_DIR, nm + ".vrp")
    dim, cap, coords, dem = load_vrp(p)
    G = np.array([[grader_dist(coords, i, j) for j in range(dim)] for i in range(dim)])
    raw = vrplib.read_instance(p)["edge_weight"]  # float euclidean
    npairs += dim * dim
    for k, f in ROUND_FUNCS.items():
        M = np.asarray(f(raw))
        d = np.abs(M - G)
        counts[k] += int((M == G).sum())
        worst[k] = max(worst[k], float(d.max()))
print(f"\n[B] elementwise match vs grader _dist over {npairs} pairs ({len(sample_b)} instances):")
for k in ROUND_FUNCS:
    print(f"    round_func={k:8s} exact-match={counts[k]:7d}/{npairs} "
          f"({100*counts[k]/npairs:6.2f}%)  max|diff|={worst[k]:.1f}")

# ---- C) HGS reported cost == grader_cost(HGS routes)? ------------------------
sample_c = random.sample(names, 8)
print("\n[C] PyVRP HGS (round_func='round', 2s, seed=42) cost vs grader recompute:")
allok = True
for nm in sample_c:
    p = os.path.join(INST_DIR, nm + ".vrp")
    dim, cap, coords, dem = load_vrp(p)
    cost, routes, nr, feas = solve_hgs(p, 2.0, seed=42)
    g = grader_cost(coords, routes)
    visits = sorted(c for r in routes for c in r)
    ok = (cost == g) and visits == list(range(1, dim)) and feas
    allok &= ok
    print(f"    {nm}: pyvrp={cost:6d} grader={g:6d} diff={cost-g:+d} routes={nr} "
          f"feas={feas} valid_perm={visits==list(range(1,dim))} {'OK' if ok else 'FAIL'}")
print(f"[C] all agree: {allok}")
