---
name: jssp-calibrate
description: Score solution.solve() against OR-Library instances with published optima, to separate "my search is weak" from "the lower bound is loose". Run after any change to the search engine.
creator: captain-ahab
created: 2026-07-09T17:45:00+00:00
---
# What it does

`evaluate_local.py` reports gap vs `max(machine load, job chain)`. That bound is
**not tight**: on ta01 (15x15) the *proven optimum* is already +26.0% above it. So a
"42% gap" tells you nothing about whether your search is bad or the bound is loose.

This script runs `solve()` on `benchmarks/*.jss`, which ship **published optima**, and
prints both gaps side by side plus the difference (= how many gap points are unwinnable).

# When to use it

- After ANY change to the search engine (neighbourhood, tabu rules, acceptance, LNS).
- Before concluding "we are far from optimal" from an `evaluate_local.py` number. You cannot.
- To decide whether to invest in search quality at all.

# How to use it

    python .claude/skills/jssp-calibrate/scripts/calibrate.py [time_limit] [instance ...]

Defaults to 10 s and all 10 benchmark instances (~100 s). For a fast check:

    python .claude/skills/jssp-calibrate/scripts/calibrate.py 3 ft10 la21 swv01

# Reading the output

    mean gap vs OPTIMUM = 1.28%    <- your search quality. THIS is what you can improve.
    mean gap vs LB      = 26.45%   <- what evaluate_local.py would have shown
    LB looseness        = 25.17 pts <- unwinnable

Reference: as of `aacf9b8e` the N5 tabu engine scores **1.28%** vs optimum (exact on
ft10, ft20, la26). `swv01` is the outlier at +8.53% — structured instances need TSAB-style
elite backtracking, which plain N5 tabu lacks.

Caveat: benchmark instances are small (<= 20x15). They certify per-iteration search
*quality*, not behaviour at 10,000 operations where iteration *count* binds instead.

---

# Second tool: `strong_lb.py` — how loose is the grader's bound?

    python .claude/skills/jssp-calibrate/scripts/strong_lb.py

The grader's `lower_bound = max(busiest machine load, longest job chain)` ignores that an
operation cannot start before its job prefix has run, nor finish later than its job suffix
allows. The **one-machine relaxation** repairs that: for machine m give each of its operations
a head `r_j` (job prefix) and tail `q_j` (job suffix), relax every other machine, and solve
`1|r_j,q_j,pmtn|Cmax` exactly with Jackson's Preemptive Schedule in O(k log k). Preemption only
helps, so JPS(m) lower-bounds the JSSP makespan. Take the max over machines.

Validated against all 10 published optima — it never exceeds the optimum, and averages ~93% of it
(vs the grader's bound at ~75-80%):

| instance | grader LB | strong LB | lift | optimum | strongLB/opt |
|---|---|---|---|---|---|
| ft10 | 655 | 808 | +23.4% | 930 | 86.9% |
| orb01 | 695 | 929 | +33.7% | 1059 | 87.7% |
| ta01 | 977 | 1168 | +19.5% | 1231 | 94.9% |
| la26 | 1218 | 1218 | +0.0% | 1218 | 100.0% |
| ft20 | 1119 | 1164 | +4.0% | 1165 | 99.9% |

On the visible instances the grader's bound is loose by **+8.5%** (train_100x100_a: 5721 → 6205)
and **+20.2%** (train_020x020_a: 1245 → 1497).

**Why you care.** A reported "49% gap over LB" at 100x100 is at most a 38.7% gap over a bound
that is itself provably valid — and the true optimum is higher still. Do not read the grader's
gap as distance from optimality; it overstates it badly, and the overstatement is *size-dependent*,
so it distorts where you think the headroom is.
