"""De-aliased replication sample (30 clean frozen instances).

sample30.py used A=i%3+1 and D=i%6+1, which makes A a deterministic function of
D (A == ((D-1) % 3) + 1) -- the depot factor is perfectly confounded with the
route-size factor. All levels still appear, so the pooled gap numbers from that
sample are valid, but a per-D breakdown there is really a per-(D,A) breakdown.

Here D is the block factor (5 instances per level, the known difficulty driver)
and A cycles independently within blocks, so A is NOT a function of D.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import INST_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
corrupt = {l.split("\t")[0] for l in open(os.path.join(HERE, "corrupt_sols.txt"))}
available = {n[:-4] for n in os.listdir(INST_DIR)} - corrupt

rng = random.Random(11)
picked, combos = [], []
for i in range(30):
    D = i // 5 + 1        # 1..6, five each  (blocked)
    A = i % 3 + 1         # 1..3, ten each   (cycles within blocks -> not f(D))
    B = (i // 2) % 3 + 1  # 1..3, ten each
    C = i % 7 + 1         # 1..7, all levels
    combos.append((A, B, C, D))
    cands = sorted(n for n in available
                   if n.startswith(f"XML100_{A}{B}{C}{D}_") and n not in picked)
    if not cands:
        raise SystemExit(f"no clean instance for {A}{B}{C}{D}")
    picked.append(rng.choice(cands))

assert len(set(combos)) == 30, f"only {len(set(combos))} distinct combos"
assert len(set(picked)) == 30
# the whole point: A must not be determined by D
byD = {}
for A, B, C, D in combos:
    byD.setdefault(D, set()).add(A)
assert all(len(v) > 1 for v in byD.values()), f"A still aliased with D: {byD}"

with open(os.path.join(HERE, "sample30b.txt"), "w") as f:
    f.write("\n".join(picked) + "\n")

for fac, pos in (("A depot", 0), ("B cust", 1), ("C demand", 2), ("D routesz", 3)):
    cnt = {}
    for c in combos:
        cnt[c[pos]] = cnt.get(c[pos], 0) + 1
    print(f"{fac:10s} {dict(sorted(cnt.items()))}")
print(f"A-levels per D level: { {d: sorted(v) for d, v in sorted(byD.items())} }")
print("\n".join(picked))
