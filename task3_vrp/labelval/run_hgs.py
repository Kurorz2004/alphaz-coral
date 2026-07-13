"""DELIVERABLES 2/3/4 — run PyVRP HGS on the 30-instance sample.

For each instance x budget {2,5,10,30}s x seed {42,43,44}:
  mode 'free'   : fleet = file default (dimension-1 = 100)  -- same as grader fallback
  mode 'pinned' : fleet = ceil(total_demand / capacity)     -- minimum feasible fleet
Records HGS cost, #routes, wall-clock, feasibility, and the proven optimum.
Output: results.csv
"""
import csv
import math
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import INST_DIR, SOL_DIR, grader_cost, load_sol, load_vrp, solve_hgs

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = [l.strip() for l in open(os.path.join(HERE, "sample30.txt")) if l.strip()]
BUDGETS = [2.0, 5.0, 10.0, 30.0]
SEEDS = [42, 43, 44]
WORKERS = 8


def job(t):
    nm, budget, seed, mode = t
    p = os.path.join(INST_DIR, nm + ".vrp")
    dim, cap, coords, dem = load_vrp(p)
    kmin = math.ceil(sum(dem) / cap)
    nveh = kmin if mode == "pinned" else None
    t0 = time.perf_counter()
    cost, routes, nr, feas = solve_hgs(p, budget, seed=seed, num_vehicles=nveh)
    wall = time.perf_counter() - t0
    # independent re-check with the grader's own distance function
    gcost = grader_cost(coords, routes)
    ok = sorted(c for r in routes for c in r) == list(range(1, dim))
    opt_routes, opt = load_sol(os.path.join(SOL_DIR, nm + ".sol"))
    # cost is None when HGS could not find a FEASIBLE solution within the fleet
    # cap (expected for mode='pinned' whenever k_min routes are not achievable).
    return dict(name=nm, budget=budget, seed=seed, mode=mode, hgs_cost=cost,
                grader_cost=gcost, opt=opt, n_routes=nr, kmin=kmin,
                opt_routes=len(opt_routes), feasible=int(feas), valid_perm=int(ok),
                wall=round(wall, 3),
                gap_pct=(100.0 * (cost - opt) / opt) if feas else "")


tasks = [(nm, b, s, "free") for nm in NAMES for b in BUDGETS for s in SEEDS]
tasks += [(nm, b, 42, "pinned") for nm in NAMES for b in (10.0, 30.0)]

if __name__ == "__main__":
    print(f"{len(tasks)} tasks on {WORKERS} workers "
          f"(~{sum(t[1] for t in tasks)/WORKERS/60:.1f} min)", flush=True)
    t0 = time.time()
    out = os.path.join(HERE, "results.csv")
    with Pool(WORKERS) as pool, open(out, "w", newline="") as f:
        w = None
        for i, r in enumerate(pool.imap_unordered(job, tasks, chunksize=1)):
            if w is None:
                w = csv.DictWriter(f, fieldnames=list(r))
                w.writeheader()
            w.writerow(r)
            f.flush()
            if i % 30 == 0:
                print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
    print(f"done in {time.time()-t0:.0f}s -> {out}")
