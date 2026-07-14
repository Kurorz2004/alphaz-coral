---
creator: captain-nemo
created: 2026-07-09T18:30:00+00:00
commit: 6bf73ca2a8c0
type: experiment
claim: "The N7 block-insertion neighbourhood helps exactly where the O(N) graph update dominates (N>900) and hurts where it does not; size-gating it gives +0.0033"
status: confirmed
confidence: high
evidence:
  attempt: 6bf73ca2a8c0
  score_delta: 0.715539 → 0.718810
  verified: true
based_on: [50904972, d58269a7]
touched: [solution.py, lns_probe.py]
tags: [neighbourhood, N7, balas-vazacopoulos, acyclicity, lns, falsification]
---

# N7 block insertion, size-gated: a wider neighbourhood is free only when the update dominates

## Context

Following the cost-model finding in [eval-2](eval-2-incremental-eval-batched-moves.md):
one O(N) heads/tails repair costs ~4.4ms at N=10000, while one O(1) move estimate
costs ~1 microsecond. The N5 neighbourhood evaluates only ~46 moves per update.
So the update should buy a *better* move, not just more moves. N7
(Balas-Vazacopoulos) moves an operation to the front or back of its critical
block instead of only swapping block ends.

## Result

| Instance (local, 10s) | N5 | N7 | Δ |
|---|---|---|---|
| 20x20_a | 1586 | 1776 | **+12.0% worse** |
| 20x20_b | 1571 | 1700 | **+8.2% worse** |
| 50x50_a | 4247 | 4157 | -2.1% |
| 50x50_b | 4235 | 4211 | -0.6% |
| 100x100_a | 8683 | 8591 | -1.1% |
| 100x100_b | 8696 | 8589 | -1.2% |

20x20 regression confirmed over 5 seeds (mean 1605.8 → 1786.4 on `a`;
1586.2 → 1714.4 on `b`) — not noise.

Shipped config: `N > 900` → N7 + batch 4; else N5 + batch 1.
Local 15s 0.7318 → 0.7343. **score: 0.718810** (real, from 0.715539).

## Mechanism

Two O(1) acyclicity conditions, derived rather than tested for (testing would cost
an O(N) Kahn per candidate, which is the entire budget):

- **Forward** (move `u` to just after `v`): the only new backward arc is `v -> u`,
  so a cycle needs a path `u ~> v`. Every predecessor of `u` other than `v` has a
  smaller head, so such a path must leave `u` by its job successor `js[u]`; and a
  path `js[u] ~> v` forces `q[js[u]] >= dur[js[u]] + q[v] > q[v]`. Hence
  **`q[js[u]] <= q[v]` proves acyclicity.**
- **Backward** (move `v` to just before `u`): a cycle again needs `u ~> v`; in the
  new graph `v`'s only reachable predecessor is `jp[v]`, and any path `u ~> jp[v]`
  forces `r[jp[v]] >= r[u] + dur[u]`. Hence
  **`r[jp[v]] < r[u] + dur[u]` proves acyclicity.**

Verified: ~16k iterations with incremental `r`/`q`/`cmax` asserted equal to a full
recompute; zero cycles ever raised. The estimator was separately verified to be a
true lower bound — **0 violations in 9238 applied moves**.

**Why the size split.** The estimate is a *lower bound* on the post-move makespan,
and it is exact 91% of the time at 20x20 but only **4% of the time at 100x100**.
Best-improvement takes the `argmin` over the neighbourhood. The larger the
neighbourhood, the more the argmin selects the candidate whose bound is *loosest*,
not the move that is truly best — the optimizer's curse. At small N the update is
cheap, N5 already converges, and this selection bias is pure cost. At large N the
update swamps everything, so even a biased pick from a wider neighbourhood is a
better use of the 4.4ms.

**This is the same inversion that governs batching** (eval-2: batch 4 helps 50x50
and 100x100, hurts 20x20). Two independent levers, one underlying cause. See
[_synthesis/cost-model-inversion.md](../_synthesis/cost-model-inversion.md).

## What did not work

- **Machine-reinsertion LNS — falsified, do not rebuild.** Rip out one machine's
  sequence, recompute heads/tails on the graph without it, re-sequence by Schrage
  for `1|r_j,q_j|Lmax`, accept if the exact makespan improves. On 100x100: **5
  accepted out of 1813 reinsertions**; 30s of sweeps moved 9218 → 9210 while tabu
  reached 8590 in 9s. Diagnostic: Schrage changes ~10 of 100 positions on 99/100
  machines, yet **median Δcmax = 0** (best −2, worst +94). So the move is genuinely
  near-neutral, not mis-implemented. Reordering one machine against frozen
  heads/tails cannot move a critical path that threads through many machines.
  captain-ahab reached the same conclusion independently (6 improvements / 713
  reopts, `552950a2`). **This is the objective's own hint and it is wrong in this
  regime.** Code kept at `lns_probe.py` as the falsifying experiment.
- **Multiprocessing / best-of-k restarts — falsified.** 16 parallel runs @9s on
  100x100: best 8742, spread only 67. One single 144s run: **8245**. Best-of-16 is
  *worse* than one uncontended 9s run (8590) — CPU contention costs more than
  restart diversity gains. Search *depth* is everything; breadth is worthless
  because the seed-to-seed variance (0.8%) is far smaller than the time-depth
  gradient. Do not build an island model.
- **heapq-ordered incremental propagation** (eval-2) — superseded by a linear sweep.

## Surprises / open questions

- I expected LNS to be the big win; it was the biggest dud. I expected
  multiprocessing to be a safe +0.01; it is *negative*. Both of my top-two
  predicted levers from eval-2 were wrong, and the lever I ranked fourth (N7) was
  the one that paid. **My ranking of untested levers is not reliable; the cheap
  falsifying probe is.** Each of these took <20 minutes to kill.
- The 100x100 curve is flat but not hopeless: 8590 @9s, 8245 @144s. That is
  ~0.007 ratio per doubling of compute, i.e. **each 2x inner-loop speedup is worth
  roughly +0.005 score.** `incr_heads`+`incr_tails` are now 87% of runtime and the
  cost is array *traversal*, not recompute — close to the pure-Python floor.
- Still open, and load-bearing for the whole team: is `opt/LB ~ 1.30` really
  scale-invariant for square Taillard instances? If the true 100x100 ratio is
  ~1.45, we are within 3% of optimal there and the remaining headroom is fake.

## Next

1. **20x20 multi-restart.** 20x20 converges well inside the budget (12x time buys
   0.7%), and seed spread is ~1.2% (min 1586 vs mean 1606 over 5 seeds). Spending
   the idle budget on independent restarts and keeping the best should recover most
   of that spread on 3 of 9 instances. Expected +0.003..0.005. Risk: none; it is
   strictly best-of. **Cheapest remaining win.**
2. **Raise the time budget from 0.90 to 0.95 of `time_limit`.** Free ~5% compute.
   Expected +0.001..0.002. Risk: none, wall timeout is 3x+60s.
3. **Tenure / batch retune under N7.** The tenure `6..10+N/100` and `batch=4` were
   tuned under N5. Expected +0.002..0.005. Risk: overfitting to 6 visible instances.
4. **Falsify `opt/LB ~ 1.30`.** Not a score lever, but it decides whether anyone
   should keep pushing 100x100. Highest *information* value.

## References

- attempt `6bf73ca2` (this), `50904972`, `d58269a7` — my chain.
- attempt `552950a2` (captain-ahab): independent falsification of machine-LNS.
- prior note: [eval-2-incremental-eval-batched-moves.md](eval-2-incremental-eval-batched-moves.md)
  — the cost model this move is derived from, and the batching precedent for the
  size split.
- prior note: [eval-3-nondelay-constructor-port.md](eval-3-nondelay-constructor-port.md)
  — the "local 15s is ~1.5x optimistic vs real 9s" calibration used to read the
  0.7343-local / 0.7188-real gap here.
- prior note: [eval-1-tabu-engine-and-optimality-calibration.md](eval-1-tabu-engine-and-optimality-calibration.md)
  (captain-ahab) — the engine-vs-bound calibration.
- Balas & Vazacopoulos (1998), *Guided local search with shifting bottleneck for
  job shop scheduling*; Nowicki & Smutnicki (1996); Taillard (1994).
