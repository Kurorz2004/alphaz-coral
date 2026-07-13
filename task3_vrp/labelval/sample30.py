"""Pick 30 frozen XML100 instances SPANNING the ABCD parameter space.

Name = XML100_ABCD_ID: A=depot pos 1-3, B=customer pos 1-3, C=demand type 1-7,
D=avg route size 1-6. We stride each factor independently so all levels of all
four factors appear. Corrupt .sol files (see audit_all_sols.py) are excluded.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import INST_DIR, SOL_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
corrupt = {l.split("\t")[0] for l in open(os.path.join(HERE, "corrupt_sols.txt"))}
available = {n[:-4] for n in os.listdir(INST_DIR)} - corrupt

rng = random.Random(7)
picked, combos = [], []
for i in range(30):
    A = i % 3 + 1
    B = (i // 3) % 3 + 1
    C = i % 7 + 1
    D = i % 6 + 1
    combos.append((A, B, C, D))
    cands = sorted(n for n in available
                   if n.startswith(f"XML100_{A}{B}{C}{D}_") and n not in picked)
    if not cands:
        raise SystemExit(f"no clean instance for {A}{B}{C}{D}")
    picked.append(rng.choice(cands))

assert len(set(combos)) == 30, f"only {len(set(combos))} distinct combos"
assert len(set(picked)) == 30
with open(os.path.join(HERE, "sample30.txt"), "w") as f:
    f.write("\n".join(picked) + "\n")

for fac, pos in (("A depot", 0), ("B cust", 1), ("C demand", 2), ("D routesz", 3)):
    lv = sorted({c[pos] for c in combos})
    cnt = {v: sum(1 for c in combos if c[pos] == v) for v in lv}
    print(f"{fac:10s} levels covered {lv} counts {cnt}")
print("\n".join(picked))
