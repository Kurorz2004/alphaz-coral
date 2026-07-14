---
creator: captain-ahab
created: 2026-07-09T18:15:00+00:00
commit: 552950a26894
type: experiment
claim: "Because one N5 swap already dirties 35-43% of the disjunctive graph, K node-disjoint critical-block swaps can share a single O(N) recompute -- buying ~8x the moves per second at 100x100 for no extra repair cost."
status: confirmed
confidence: high
evidence:
  attempt: 552950a26894
  score_delta: "0.7028 -> 0.7107 (+0.0079)"
  verified: true
based_on: [aacf9b8e8b60, b283cf1bfbb9]
touched: [solution.py]
tags: [tabu-search, large-neighbourhood, batched-moves, acyclicity, kahn, throughput]
---

# Batched critical-block swaps: 0.7028 -> 0.7107, and the acyclicity risk is real but only at small N

## Context

Real mode, hidden set, 10 s/instance. Structural attempt 1/3 in the large-neighbourhood lane
declared in [focus-captain-ahab-tabu-engine](../focus/focus-captain-ahab-tabu-engine.md).
Builds directly on the profiling in
[eval-1](eval-1-tabu-engine-and-optimality-calibration.md), which established that exact
incremental repair has a ~2.5x ceiling because the affected set is 35% of heads / 43% of tails.

The inversion that motivated this eval: **if one move already dirties a third of the graph, the
repair cost is nearly the same for eight moves as for one.** So stop paying per move.

## Result

| Metric | eval 1 (`b283cf1b`) | eval 2 (`aacf9b8e`) | eval 3 (`552950a2`) |
|---|---|---|---|
| **hidden score** | 0.6916 | 0.7028 | **0.7107** |
| hidden mean gap vs LB | 45.21% | 42.76% | 41.04% |
| hidden 20x20 gap | 34.3% | 33.0% | 33.0% |
| hidden 50x50 gap | 44.0% | 42.9% | 41.1% |
| hidden 100x100 gap | 57.3% | 52.4% | **49.1%** |
| local 9 s score | 0.7102 | 0.7123 | 0.7224 |

**score: 0.7107** — past the task's stated "competent Nowicki-Smutnicki tabu" reference of 0.7038.

### K sweep, `train_100x100_a`, 9 s (fixed batch size, no restart)

| K | 1 | 2 | 3 | 5 | 8 | 16 |
|---|---|---|---|---|---|---|
| Cmax | 8873 | 8825 | 8786 | 8702 | **8636** | 8642 |
| super-iterations | 1078 | 1045 | 1030 | 1036 | 1049 | 1032 |

Super-iteration count is flat in K — that is the whole point. Moves per second scale with K
essentially for free until K ~ 8.

Tuned on the four large visible instances: `(KDIV, KCAP, STAGB) = (3, 8, 600)` → mean ratio
0.6797, versus (5, 10, 300) → 0.6759. `kmax = n_blocks // 3`, clamped to [2, 8].

## Mechanism

- **Batching converts a fixed O(N) cost into an amortised one.** A super-iteration is
  `critical_blocks` (0.06 ms) + estimates (0.06 ms) + one Kahn heads pass + one tails pass.
  Everything except the two O(N) passes is noise, and those passes do not care how many arcs
  were reversed since the last one.
- **Kahn's settled-node count is a free acyclicity test.** A *single* critical-block swap is
  provably acyclic (Nowicki-Smutnicki); a *batch* is not. But the heads recompute already runs
  Kahn, and `len(order) < N` iff the graph has a cycle. On a cycle: undo the batch, apply only
  the single best move (always safe). Zero extra cost in the common case.
- **Kahn's pop order is a topological order.** Tails were being computed by a second Kahn with
  its own in-degree build. Feeding the heads pass's pop order backwards into a plain reverse
  sweep gives identical tails at 0.32 ms vs 0.94 ms (50x50) — a 3x cut on ~25% of the iteration.
  Verified exact against `_full_tails` on 2500 nodes.
- **K decays past ~8 because the estimates are mutually blind.** Each candidate's Taillard bound
  assumes the *other* K-1 moves in the batch did not happen. Node-disjointness keeps them from
  corrupting each other's arithmetic, but not from interacting through the graph.

## What did not work

- **Machine-reoptimisation LNS / shifting-bottleneck refinement.** This was my *stated* top pick
  in eval 1's Next section, with the argument that a machine reopt reorders 100 operations for
  15 ms while a tabu move relocates 1 for 6 ms. I built it: rip out a machine's arcs, recompute
  heads `r_j` and tails `q_j` on the reduced graph, re-solve `1|r_j,q_j|Cmax` with Schrage,
  reinsert, Kahn-check, revert on cycle or regression.
  **Measured on `train_100x100_a`, 9 s: 713 machine reopts, 0 cycles, and only 6 improved the
  makespan.** 9218 → 9197. Tabu over the same budget: 9218 → 8874.
  *Why it fails:* re-sequencing machine m minimises the longest path *through m* against frozen
  `r`/`q`. But Cmax is a max over many paths; almost every machine is off the critical path, so
  its reopt is a no-op, and the one bottleneck machine is already near-optimally ordered. As pure
  refinement of a complete schedule this is coordinate descent and it stalls on the first sweep.
  (Shifting bottleneck earns its reputation during *construction*, machine by machine, not as a
  refinement operator.) **Do not rebuild this.** If someone wants to revisit: the only version
  worth trying is SB as a *constructor*, and at m=100 the r/q recomputes cost ~m²/2 × 5 ms ≈ 25 s,
  which does not fit the budget. It is affordable at 50x50 (~1.6 s) and 20x20 (~0.04 s).
- **Batching *all* available block moves.** Applying every block's best move (31-48 at once)
  degrades monotonically: 9218 → 9493 → 9601 → 9730. Greedy-all is strictly worse than K=8.
- **Batching at 20x20.** Super-iterations collapsed from 12,873 to 614 and Cmax went 1617 → 1719
  (K=4) and 1889 (K=8). Cause: on a small graph the blocks sit close together, batches produce
  cycles constantly, and every cycle costs *two* full Kahn passes plus an undo. Hence the
  `N > 900` guard. The single-move incremental path is retained below that.

## Surprises / open questions

- **I was wrong about which structural idea would pay, and the profiling told me so in advance.**
  My eval-1 note ranked machine-LNS first and did not mention batching at all. The measurement
  that made batching obvious — "affected set is 35-43% of N" — was *in that same note*, filed
  under "what did not work". I had the fact and drew the wrong conclusion from it: I read it as
  "incremental repair is disappointing" instead of "repair cost is independent of move count".
- **Zero cycles at 100x100 across every trial** (12/12 trials batching 31-48 simultaneous swaps),
  yet cycles dominate at 20x20. Cycle probability appears to scale with block density on the
  critical path, not with K alone. I have not characterised this; the `N > 900` guard is empirical
  and I do not know where the true crossover is.
- 20x20 hidden results are now **byte-identical across evals 2 and 3** (1691 / 1537 / 1571).
  Consistent with the eval-1 saturation finding (33x compute → 0.8 gap points). Confirmed twice.

## Next

Descending expected payoff. Remaining headroom is ~49% gap at 100x100, ~41% at 50x50, ~0 at 20x20.

1. **Batch composition, not batch size.** Currently the K moves are the K best-estimated
   node-disjoint candidates, accepted unconditionally. Two cheap variants are running now:
   (a) admit only moves whose estimate beats the incumbent, (b) roll back the batch and fall
   back to the single best move when the batch worsens Cmax. Expected: 1-3 gap points at
   100x100, essentially free. Risk: (a) may starve the search of the non-improving moves tabu
   needs to escape; (b) doubles the Kahn cost on regressing iterations.
2. **Multiprocessing, 16 cores, stdlib, still untested.** The single biggest *unexploited*
   resource. Best-of-K independent runs is the naive scheme; note the compute curve is shallow
   (4x sequential time = 3.4 gap points) and independent restarts are worth strictly less than
   the equivalent sequential time. Expected: 1-2 gap points. Risk: unknown core count on the
   grader host; `solve()` must stay deterministic given `seed`.
   **This is the one lever I'd hand to a teammate** — it composes with everything above and
   needs no knowledge of the search internals.
3. **N7 / insertion moves** (move an operation to the front or back of its block). Richer per
   move, and unlike N5 the acyclicity condition is non-trivial. Expected: unclear; the batching
   result suggests move *count* matters more than move *quality* at 100x100.
4. **Do not** tune anything against 20x20. It is converged and will report zero for every change.

## References

- attempt `552950a2` (this): batched swaps, K sweep, `_tails_from_order`.
- attempt `aacf9b8e`: non-delay construction — the baseline this builds on.
- attempt `b283cf1b`: the heap-ordered incremental repair, still used for N <= 900.
- prior note: [eval-1-tabu-engine-and-optimality-calibration.md](eval-1-tabu-engine-and-optimality-calibration.md)
  — source of the 35%/43% affected-set measurement that motivated batching, the 1.28%-vs-optimum
  calibration, and the 20x20 saturation study. Also the note whose "Next" ranking I got wrong.
- focus note: [focus-captain-ahab-tabu-engine.md](../focus/focus-captain-ahab-tabu-engine.md)
- skill: `jssp-calibrate` — re-run after this change: small-instance quality unchanged (2.87% vs
  optimum at a 3 s budget), confirming batching did not regress the `N <= 900` path.
- Nowicki, E. & Smutnicki, C. (1996) — N5, and the single-swap acyclicity guarantee that the
  batch fallback relies on.
- Carlier, J. (1982) / Adams, Balas & Zawack (1988) — the `1|r_j,q_j|Cmax` and shifting-bottleneck
  machinery behind the LNS attempt that failed above.
