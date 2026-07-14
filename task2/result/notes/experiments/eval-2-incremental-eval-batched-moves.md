---
creator: captain-nemo
created: 2026-07-09T17:46:00+00:00
commit: d58269a72889
type: experiment
claim: "The N5 tabu bottleneck at N=10000 is the O(N) makespan recompute per move, not the neighbourhood; incremental heads/tails + batched independent swaps buy +0.016 score"
status: confirmed
confidence: high
evidence:
  attempt: d58269a72889
  score_delta: 0.694922 → 0.711058
  verified: true
based_on: [22eb3753, aacf9b8e]
touched: [solution.py, bench.py]
tags: [tabu, incremental-evaluation, disjunctive-graph, profiling, lower-bound]
---

# Incremental heads/tails + batched moves: the recompute, not the neighbourhood, was the bottleneck

## Context

`solve()` on 3x20x20 + 3x50x50 + 3x100x100 Taillard instances, ~9s each.
Engine is Giffler-Thompson(MWKR) construction + Nowicki-Smutnicki N5 tabu with
Taillard's O(1) move estimates. Eval #1 (`22eb3753`) landed at 0.694922, which is
*exactly* the task's quoted "competent tabu" reference of 0.7038-at-20s. This note
covers eval #2 (`d58269a7`).

## Result

| Metric | Baseline `22eb3753` | This `d58269a7` | Δ |
|---|---|---|---|
| real score | 0.694922 | 0.711058 | **+0.016136** |
| local score (15s) | 0.7077 | 0.7248 | +0.0171 |
| iters/sec @ N=400 | 4498 | ~5900 | 1.3x |
| iters/sec @ N=2500 | 701 | ~1600 | 2.3x |
| iters/sec @ N=10000 | 180 | ~270 | 1.5x |
| moves/sec @ N=10000 | 180 | ~1080 | 6.0x |

**score: 0.711058**

## Mechanism

Two independent changes, both flowing from one profiling fact: **a full
heads+tails recompute costs 4.9ms at N=10000, while one Taillard move estimate
costs ~1 microsecond.** The search was spending >90% of its time re-deriving the
graph and only ~42 estimates per update. The cost model is inverted relative to
what N5 was designed for.

1. **Incremental heads/tails over a maintained topological order.**
   Key lemma: *sorting operations by head value yields a valid topological order*,
   because every arc `x -> y` satisfies `r[y] >= r[x] + dur[x] > r[x]` (all
   durations >= 1, so the increase is strict). An N5 swap flips exactly one arc,
   and both its endpoints lie inside the position window `[pos[u], pos[v]]`, so
   re-running Kahn *inside that window only* restores validity and provably
   touches nothing outside it (every node's predecessors already sit at smaller
   positions). Measured mean window: **11 / 27 / 60 nodes** at 20x20 / 50x50 /
   100x100 — tiny, exactly as the head-sorted argument predicts. Heads and tails
   are then repaired by one forward and one backward dirty-flag sweep, each
   terminating as soon as the wavefront dies.

2. **Batched independent moves.** Because one update is O(N) and one estimate is
   O(1), each update should buy more than one move. Applying `k` swaps at once is
   **provably acyclic** if (a) each reversed pair is machine-adjacent with a tight
   head `r[v] = r[u] + dur[u]` — which holds automatically for two consecutive
   critical operations — and (b) no two selected pairs are graph-adjacent. Proof:
   every non-reversed arc strictly increases `r`; a hypothetical cycle through the
   reversed arcs must traverse a path of >= 2 arcs between distinct pairs, forcing
   `r[v_{t+1}] >= r[v_t] + 1`, hence `r[v_1] >= r[v_1] + k`. Contradiction.

Both were validated by asserting incremental `r`, `q` and `cmax` against a full
recompute on **every one of ~11,000 batched iterations** across all three sizes.
No divergence, no cycle.

## What did not work

- **heapq-ordered propagation** — my first incremental version popped nodes by
  topological position from a binary heap. Profiling showed **5.36M heappush/pop
  over 1167 iterations** (~4600 pops/move, i.e. ~23% of the graph changes per
  swap) costing 27% of runtime. Net speedup was only **1.6x**. Replacing the heap
  with a linear dirty-flag sweep over `order` removed the log factor and the
  Python call overhead. Lesson: when the changed set is a large *fraction* of N, a
  heap is pure overhead — sweep instead.
- **Large batch sizes.** Sweep at 10s (`_BATCH` override), mean ratio over the
  three "a" instances: b=1 → 0.7117, b=4 → 0.7087, b=8 → 0.6950, b=16 → 0.6658,
  b=32 → 0.6428. But this *average* hides an interaction with size: 20x20 degrades
  monotonically (1609 → 1681 → 1731 → 1740), whereas 50x50 (4259 → 4180) and
  100x100 (8911 → 8767) improve at b=4. 20x20 is already converged, so extra
  simultaneous moves only inject noise. Hence `batch = 1 if N <= 900 else 4`.
- **Seeding propagation only from `u` and `v`.** First incremental build asserted
  out immediately (`cmax 2172 != 2099`). The swap rewires `a -> v -> u -> b`, so
  `b`'s *predecessor* set changes (heads must be reseeded at `b`) and `a`'s
  *successor* set changes (tails must be reseeded at `a`). If `r[u]` happens not
  to change, `b` is never pushed and goes silently stale.

## Surprises / open questions

- **The lower bound is loose, and that is most of the "gap".** Calibrating against
  OR-Library instances with *published optima* (`bench.py`, and independently
  captain-ahab's `jssp-calibrate` skill): this engine hits the **proven optimum**
  on ft10 (930), abz5 (1234), la16 (945), and is within 1.4% on ta01. Yet
  `optimum/LB` on square instances is 1.42 (ft10), 1.32 (la16), 1.26 (ta01), 1.23
  (la36). So `LB/optimum` is about 0.79 at 15x15 — **even a perfect solver scores
  ~0.79 on a square instance.** The score is not "% of optimal", exactly as
  CLAUDE.md warns.
- **20x20 is already converged.** 12x more time (10s → 120s) moves 20x20_a only
  1611 → 1600 (-0.7%). Its 29% "gap" is essentially all bound looseness. There is
  <1% to win there. **Do not spend effort on 20x20.**
- **100x100 tabu is brutally flat.** Convergence probe on train_100x100_a:
  10s → 8908, 60s → 8587 (-3.6%), 300s → 8355 (-6.2%). 50x50_a: 10s → 4324,
  60s → 4117, 300s → 4053. Extrapolating the square `opt/LB ~ 1.30` ratio gives an
  estimated optimum of ~3980 for 50x50_a (we are at 4070) and ~7440 for 100x100_a
  (we are at 8720). **The remaining headroom is almost entirely at 100x100, and
  30x more single-core compute only recovers 6% of it.** More iterations of the
  same tabu will not close this. A different algorithm is needed at that size.
- Open: is `opt/LB ~ 1.30` really scale-invariant for square Taillard instances?
  It is an extrapolation from 15x15/20x20 plus my 300s asymptote, not a proof. If
  the true 100x100 ratio is ~1.45, most of the apparent 100x100 headroom is fake.
  **Someone should try to falsify this** — it decides where the whole team spends
  its remaining evals.

## Next

In descending expected payoff:

1. **A large-neighbourhood / decomposition method for 100x100** — rip out one
   machine's sequence and re-optimise it against fixed heads/tails
   (`1|r_j,q_j|Lmax` via Schrage), sweeping all m machines. One machine re-opt
   costs ~2 O(N) passes but reorders up to 100 operations, versus one adjacent
   swap. This is the only lever I see that can beat the flat tabu curve at
   N=10000. Expected +0.02..0.05. Risk: Schrage is a heuristic for an NP-hard
   subproblem; a sweep can worsen the makespan and needs accept/reject.
2. **Adopt captain-ahab's non-delay construction** (`aacf9b8e`): non-delay+MWKR
   gives 55.5% mean gap vs my active-GT 68.9%. Stacks with my faster engine — my
   init at 100x100_a is 9915, which is poor. Expected +0.005..0.015. Risk: none,
   it is a strict swap of the constructor. Cheap; do first.
3. **Multiprocessing across the 16 available cores** — best-of-k with periodic
   migration from the global best. Expected +0.005..0.02, *smaller than it looks*
   because the 100x100 curve is flat: 16 independent runs is worth far less than
   one 16x-longer run. Risk: core count on the grader host is unverified; must
   fall back to single-process cleanly.
4. **N7 / insertion neighbourhood (Balas-Vazacopoulos)** — strictly stronger moves
   for the same update cost. Expected +0.01..0.03. Risk: O(block length) per
   estimate, and a more intricate correctness argument.

## References

- attempt `22eb3753`: my baseline N5 tabu; established that a textbook-correct
  implementation lands exactly on the quoted 0.7038 reference.
- attempt `aacf9b8e` (captain-ahab): non-delay beats active Giffler-Thompson
  (55.5% vs 68.9% mean gap); independently confirmed the bound-looseness finding
  via `jssp-calibrate`. I take the constructor from this, and the corroboration of
  "the engine is not the problem on small instances".
- skill: `jssp-calibrate` (captain-ahab) — calibrate the engine against published
  optima before concluding the *search* is weak.
- Taillard (1993) benchmark generator; Taillard (1994) O(1) move estimates;
  Nowicki & Smutnicki (1996) N5 / TSAB.
