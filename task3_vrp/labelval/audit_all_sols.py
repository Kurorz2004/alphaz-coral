"""Full audit of all 10,000 frozen .sol files against the grader's validity rules.

Checks: (1) Cost line == grader_cost(routes); (2) routes are a permutation of
1..n-1 (each customer exactly once); (3) every route respects CAPACITY.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import INST_DIR, SOL_DIR, grader_cost, load_sol, load_vrp

names = sorted(n[:-4] for n in os.listdir(INST_DIR))
bad_cost, bad_perm, bad_cap = [], [], []
for k, nm in enumerate(names):
    dim, cap, coords, dem = load_vrp(os.path.join(INST_DIR, nm + ".vrp"))
    routes, cost = load_sol(os.path.join(SOL_DIR, nm + ".sol"))
    if grader_cost(coords, routes) != cost:
        bad_cost.append(nm)
    cnt = Counter(c for r in routes for c in r)
    if sorted(cnt) != list(range(1, dim)) or any(v > 1 for v in cnt.values()):
        dup = sorted(c for c, v in cnt.items() if v > 1)
        miss = [c for c in range(1, dim) if cnt[c] == 0]
        bad_perm.append((nm, dup, miss))
    if any(sum(dem[c] for c in r) > cap for r in routes):
        bad_cap.append(nm)
    if k % 2000 == 0:
        print(f"  ...{k}/{len(names)}", flush=True)

n = len(names)
print(f"\nAudited {n} .sol files")
print(f"  Cost line != grader recompute : {len(bad_cost)} ({100*len(bad_cost)/n:.2f}%) {bad_cost[:5]}")
print(f"  not a permutation of customers: {len(bad_perm)} ({100*len(bad_perm)/n:.2f}%)")
print(f"  capacity violated             : {len(bad_cap)} ({100*len(bad_cap)/n:.2f}%) {bad_cap[:5]}")
for nm, dup, miss in bad_perm[:15]:
    print(f"    {nm}: duplicated={dup} missing={miss}")
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corrupt_sols.txt"), "w") as f:
    for nm, dup, miss in bad_perm:
        f.write(f"{nm}\tdup={dup}\tmiss={miss}\n")
