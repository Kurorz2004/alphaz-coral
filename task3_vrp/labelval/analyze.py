"""Analysis of results.csv -> deliverables 2 (labeler quality), 3 (fleet), 4 (cost).

Usage: python analyze.py [results.csv]

Protocol note: the OPERATIONAL labeling protocol is ONE HGS run at a fixed seed,
so the headline table is seed=42 only. The 3-seed pooled table and the seed-to-
seed spread are reported so a single run is not mistaken for a stable number.
"""
import csv
import statistics as st
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.csv")
rows = list(csv.DictReader(open(path)))
for r in rows:
    r["budget"] = float(r["budget"])
    r["seed"] = int(r["seed"])
    r["opt"] = int(r["opt"])
    r["n_routes"] = int(r["n_routes"])
    r["kmin"] = int(r["kmin"])
    r["opt_routes"] = int(r["opt_routes"])
    r["feasible"] = int(r["feasible"])
    r["valid_perm"] = int(r["valid_perm"])
    r["wall"] = float(r["wall"])
    r["hgs_cost"] = int(r["hgs_cost"]) if r["hgs_cost"] not in ("", "None") else None
    r["gap_pct"] = float(r["gap_pct"]) if r["gap_pct"] not in ("", "None") else None

free = [r for r in rows if r["mode"] == "free"]
pinned = [r for r in rows if r["mode"] == "pinned"]
budgets = sorted({r["budget"] for r in free})
insts = sorted({r["name"] for r in free})
print(f"file={os.path.basename(path)}  rows={len(rows)}  free={len(free)}  "
      f"pinned={len(pinned)}  instances={len(insts)}  budgets={budgets}")

# ---- integrity: HGS cost must equal the grader's recompute, always -----------
bad = [r for r in rows if r["feasible"] and r["hgs_cost"] != int(r["grader_cost"])]
badperm = [r for r in rows if not r["valid_perm"]]
print(f"\n[integrity] feasible runs where pyvrp cost != grader recompute: {len(bad)}")
print(f"[integrity] runs whose routes are not a permutation of customers: {len(badperm)}")


def stats(rs):
    """% exact-optimal, mean gap, max gap over a set of runs."""
    g = [r["gap_pct"] for r in rs]
    exact = sum(1 for r in rs if r["hgs_cost"] == r["opt"])
    return len(rs), 100.0 * exact / len(rs), st.mean(g), max(g)


# ---- DELIVERABLE 2: labeler quality ----------------------------------------
print("\n=== D2. HGS vs PROVEN OPTIMUM (free fleet) ===")
print("\n(a) OPERATIONAL protocol: single run, seed=42")
print(f"{'budget':>7} {'n':>4} {'%exact':>8} {'mean gap%':>10} {'MAX gap%':>9}")
for b in budgets:
    rs = [r for r in free if r["budget"] == b and r["seed"] == 42]
    n, ex, mg, xg = stats(rs)
    print(f"{b:6.0f}s {n:4d} {ex:7.1f}% {mg:10.3f} {xg:9.3f}")

print("\n(b) POOLED over seeds 42/43/44 (3x the sample; guards against a lucky seed)")
print(f"{'budget':>7} {'n':>4} {'%exact':>8} {'mean gap%':>10} {'MAX gap%':>9}")
for b in budgets:
    rs = [r for r in free if r["budget"] == b]
    n, ex, mg, xg = stats(rs)
    print(f"{b:6.0f}s {n:4d} {ex:7.1f}% {mg:10.3f} {xg:9.3f}")

print("\n(c) SEED SPREAD: per-budget %exact / mean-gap for each seed separately")
print(f"{'budget':>7}  " + "  ".join(f"seed{s}:%exact/mean" for s in (42, 43, 44)))
for b in budgets:
    cells = []
    for s in (42, 43, 44):
        rs = [r for r in free if r["budget"] == b and r["seed"] == s]
        _, ex, mg, _ = stats(rs)
        cells.append(f"{ex:5.1f}%/{mg:.3f}")
    print(f"{b:6.0f}s  " + "        ".join(cells))

print("\n(d) BEST-OF-3-SEEDS per instance (cost = min over 3 seeds at that budget)")
print(f"{'budget':>7} {'n':>4} {'%exact':>8} {'mean gap%':>10} {'MAX gap%':>9} {'cpu-s/inst':>11}")
for b in budgets:
    ex = mg = 0
    gaps = []
    for nm in insts:
        rs = [r for r in free if r["budget"] == b and r["name"] == nm]
        best = min(r["hgs_cost"] for r in rs)
        opt = rs[0]["opt"]
        gaps.append(100.0 * (best - opt) / opt)
        ex += best == opt
    print(f"{b:6.0f}s {len(insts):4d} {100*ex/len(insts):7.1f}% {st.mean(gaps):10.3f} "
          f"{max(gaps):9.3f} {3*b:11.0f}")

# ---- where does it fail? by D (avg route size) ------------------------------
print("\n(e) Gap by D (avg route size digit), seed=42 -- D=1 is the known hard case")
Ds = sorted({r["name"].split("_")[1][3] for r in free})
print(f"{'budget':>7} " + " ".join(f"{'D=' + d:>14}" for d in Ds))
for b in budgets:
    cells = []
    for d in Ds:
        rs = [r for r in free if r["budget"] == b and r["seed"] == 42
              and r["name"].split("_")[1][3] == d]
        if not rs:
            cells.append(f"{'-':>14}")
            continue
        _, ex, mg, _ = stats(rs)
        cells.append(f"{ex:5.0f}%/{mg:6.3f}".rjust(14))
    print(f"{b:6.0f}s " + " ".join(cells))

# worst instances at 10s
print("\n(f) worst instances @10s seed=42:")
w = sorted([r for r in free if r["budget"] == 10.0 and r["seed"] == 42],
           key=lambda r: -r["gap_pct"])[:6]
for r in w:
    print(f"    {r['name']}  gap={r['gap_pct']:6.3f}%  hgs={r['hgs_cost']} opt={r['opt']} "
          f"k_hgs={r['n_routes']} k_opt={r['opt_routes']} kmin={r['kmin']}")

# ---- DELIVERABLE 3: fleet ---------------------------------------------------
print("\n=== D3. FLEET ===")
print("\n(a) free-fleet HGS: does k_hgs match k_opt (routes in the proven optimum)?")
for b in budgets:
    rs = [r for r in free if r["budget"] == b and r["seed"] == 42]
    eq = sum(1 for r in rs if r["n_routes"] == r["opt_routes"])
    lt = sum(1 for r in rs if r["n_routes"] < r["opt_routes"])
    gt = sum(1 for r in rs if r["n_routes"] > r["opt_routes"])
    exceed_kmin = sum(1 for r in rs if r["n_routes"] > r["kmin"])
    print(f"  {b:5.0f}s  k_hgs==k_opt {eq:2d}/{len(rs)}   k_hgs<k_opt {lt}   "
          f"k_hgs>k_opt {gt}   (k_hgs>kmin in {exceed_kmin})")

print("\n(b) all free-fleet runs feasible?  "
      f"{sum(r['feasible'] for r in free)}/{len(free)}")
print(f"    max routes used by any free HGS run: {max(r['n_routes'] for r in free)} "
      f"(grader cap for an XML-named n=101 instance is dimension-1 = 100)")

if pinned:
    print("\n(c) PINNED fleet = k_min = ceil(total_demand/capacity)  [the UNSAFE rule]")
    for b in sorted({r["budget"] for r in pinned}):
        rs = [r for r in pinned if r["budget"] == b]
        inf = [r for r in rs if not r["feasible"]]
        print(f"  {b:5.0f}s  INFEASIBLE (HGS found no feasible sol at k_min): "
              f"{len(inf)}/{len(rs)}")
        for r in inf:
            print(f"        {r['name']}  kmin={r['kmin']} but k_opt={r['opt_routes']}")
        fs = [r for r in rs if r["feasible"]]
        if fs:
            _, ex, mg, xg = stats(fs)
            print(f"        among the {len(fs)} feasible: %exact={ex:.1f} "
                  f"mean gap={mg:.3f}% max gap={xg:.3f}%")

# ---- DELIVERABLE 4: cost ----------------------------------------------------
print("\n=== D4. LABELING COST (wall-clock per instance) ===")
print(f"{'budget':>7} {'mean wall':>10} {'max wall':>9}  overhead")
for b in budgets:
    rs = [r for r in free if r["budget"] == b]
    ws = [r["wall"] for r in rs]
    print(f"{b:6.0f}s {st.mean(ws):9.2f}s {max(ws):8.2f}s  "
          f"+{st.mean(ws)-b:.2f}s")
