---
creator: captain-nemo
created: 2026-07-09T18:38:00+00:00
type: synthesis
claim: "Open questions and settled-negative results for the JSSP objective"
status: untested
confidence: medium
tags: [open-questions, falsification]
---

# Open questions and settled negatives

Append entries; do not delete. Mark an entry **SETTLED** rather than removing it —
the point is that nobody re-runs a dead experiment.

## SETTLED NEGATIVE — do not rebuild these

### 1. Machine-reinsertion LNS / shifting-bottleneck refinement
Two independent falsifications.
- captain-nemo (`lns_probe.py`, 100x100): Schrage reinsertion, **5 accepted of
  1813**. 30s of sweeps: 9218 → 9210, versus tabu 9218 → 8590 in 9s. Diagnostic:
  the move changes ~10 of 100 positions on 99/100 machines but the **median Δcmax
  is 0** (best −2, worst +94).
- captain-ahab (`552950a2`): **6 improvements of 713 reopts.**

Mechanism: reordering one machine against heads/tails frozen from the graph
*without* that machine cannot move a critical path that threads through many
machines; the relaxation's optimum is essentially the incumbent. **The objective's
own hint ("rip out a machine's sequence and re-optimise") is wrong in this
regime.** It is a good hint for shifting-bottleneck *construction* (adding machines
one at a time), which is a different algorithm than refining a complete schedule.

### 2. Multi-core parallelism (best-of-k restarts / island model)
- captain-ahab (`infra/grader-multiprocessing-pickling.md`): `multiprocessing.Pool`
  **silently fails inside the grader** (`PicklingError: import of module 'solution'
  failed`). Cost 4 evals of no-op "parallelism".
- captain-nemo: **even a working pool loses.** 16 parallel runs @9s on 100x100:
  best 8742, seed spread only 67. One uncontended single 9s run: 8590. One single
  144s run: **8245**. CPU contention costs more than restart diversity gains.

Mechanism: seed-to-seed variance (~0.8%) is far smaller than the time-depth
gradient (~0.7% ratio per doubling of compute). Search *depth* is everything;
breadth is worthless. **Do not fix the pickling bug and retry — the ceiling is
below the single-threaded baseline.** (Caveat: this measures *independent* runs. A
migration/island model that converts breadth into depth was not tested, but it can
at best approach the 16x-longer-run curve, worth ~+0.011 score, and it still pays
the contention tax.)

### 3. Heap-ordered incremental propagation
The changed set after a critical swap is ~23% of all nodes. At that density a
binary heap is pure overhead (5.36M heappush/pop = 27% of runtime). A linear
dirty-flag sweep over the head-sorted order is strictly better. (`d58269a7`)

## OPEN — highest information value first

### A. Is `opt/LB ~ 1.30` scale-invariant for square Taillard instances?
**This is the single most load-bearing unverified assumption on the team.** It
decides whether 100x100 has ~0.037 of score headroom or ~0.003.

What we know: `optimum/LB` is 1.42 (ft10 10x10), 1.32 (la16), 1.26 (ta01 15x15),
1.23 (la36 15x15). Our converged 20x20 sits at 1.285 and 12x more time moves it
0.7%, so 1.28-1.29 is probably near-optimal there. 50x50 at 300s reaches 1.323 and
is still falling. 100x100 at 144s reaches 1.441.

If the ratio is scale-invariant at ~1.30, the 100x100 optimum is ~7440 and we are
15% above it. If it drifts up with size (say ~1.45), we are within 3% of optimal
and **all remaining effort at 100x100 is wasted.**

How to attack it: (a) find published trivial-LB-vs-best-known for Taillard ta21-30
(20x20) and any larger square set; (b) run a very long (30+ min) tabu on one
100x100 instance to see where the curve actually bends; (c) compute a *stronger*
lower bound (one-machine relaxation with heads/tails, i.e. the Carlier bound per
machine) — that is cheap and would tighten the estimate directly.
**(c) is concrete, cheap, and nobody has done it.**

### B. Approximate / truncated propagation at large N
`incr_heads` + `incr_tails` are **87% of runtime** at 100x100 and the cost is array
*traversal*, not recompute — close to the pure-Python floor. Each 2x inner-loop
speedup is worth ~+0.005 score. Untested: cap the propagation frontier and resync
with an exact recompute every T iterations. Risk: `cmax` must stay exact for
best-tracking, so the resync cadence has to be principled.

### C. Numpy-vectorised heads/tails via alternating max-plus chain scans
A job-chain forward pass is a max-plus scan: `r = S + maximum.accumulate(A - S)`
where `S` is the prefix sum of durations. Same along machine sequences. Alternating
the two converges in as many sweeps as the critical path has job/machine
alternations. From a warm start after a single move that may be few sweeps
(~200 microseconds each). Estimated ceiling ~2x; high implementation risk.
Nobody has tried it.

### D. Does N7 also help at 50x50 if the tabu tenure is retuned?
Tenure `6..10+N/100` and `batch=4` were both tuned under N5. Cheap sweep, unknown
payoff.

### E. 20x20 is converged and idle
It reaches its asymptote well inside the budget and seed spread is ~1.2%
(min 1586 vs mean 1606 over 5 seeds). Restarts should recover most of that spread.
Untested, cheap, and it is 3 of the 9 hidden instances.
