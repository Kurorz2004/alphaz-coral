"""DELIVERABLE 3 — how many routes does the PROVEN OPTIMUM use?

k_min = ceil(total_demand / capacity) is the minimum feasible fleet (bin-packing
lower bound). Question: does the optimal solution always use exactly k_min routes,
or does it sometimes need MORE? Run over every clean (non-corrupt) frozen instance.
"""
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import INST_DIR, SOL_DIR, load_sol, load_vrp

HERE = os.path.dirname(os.path.abspath(__file__))
corrupt = {l.split("\t")[0] for l in open(os.path.join(HERE, "corrupt_sols.txt"))}
names = sorted(n[:-4] for n in os.listdir(INST_DIR) if n[:-4] not in corrupt)

delta = Counter()
by_D = {}
worst = []
for nm in names:
    dim, cap, coords, dem = load_vrp(os.path.join(INST_DIR, nm + ".vrp"))
    routes, cost = load_sol(os.path.join(SOL_DIR, nm + ".sol"))
    kmin = math.ceil(sum(dem) / cap)
    d = len(routes) - kmin
    delta[d] += 1
    D = nm.split("_")[1][3]
    by_D.setdefault(D, Counter())[d] += 1
    if d > 0:
        worst.append((d, nm, len(routes), kmin))

n = len(names)
print(f"Clean instances audited: {n}\n")
print("k_opt - k_min   count      share")
for d in sorted(delta):
    print(f"  {d:+d}          {delta[d]:6d}   {100*delta[d]/n:6.2f}%")
exceed = sum(v for k, v in delta.items() if k > 0)
print(f"\nk_opt == k_min : {delta[0]} ({100*delta[0]/n:.2f}%)")
print(f"k_opt >  k_min : {exceed} ({100*exceed/n:.2f}%)")
print(f"k_opt <  k_min : {sum(v for k,v in delta.items() if k<0)} (must be 0 - k_min is a lower bound)")
print(f"max excess over k_min: {max(delta)}")

print("\nBy D (avg route size 1..6):  distribution of k_opt - k_min")
for D in sorted(by_D):
    tot = sum(by_D[D].values())
    row = " ".join(f"{d:+d}:{100*c/tot:5.1f}%" for d, c in sorted(by_D[D].items()))
    print(f"  D={D} (n={tot:4d})  {row}")

worst.sort(reverse=True)
print("\nlargest excesses:", worst[:8])
