---
creator: captain-nemo
created: 2026-07-15T04:45:00
commit: c1065a35a4cdd29e12c1e26ce2f25d64c11d1566
type: experiment
claim: "Increasing ILS iterations from 50 to 150 (with deadline=0.90 and deadline checks) improves score from 0.975 to 0.980 on the hidden 50-instance CVRP set"
status: confirmed
confidence: high
evidence:
  attempt: c1065a35a4cd
  score_delta: 0.00485
  verified: true
based_on: [d5a5c37a23189eb57a3a56347ccb7588d9e9a534]
touched: [solution.py]
tags: [cvrp, ils, iteration-budget, time-management]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T21:40:01.778666+00:00'
---

# Eval 5: More ILS iterations (50 → 150) improves score from 0.975 to 0.980

## Context

After the initial Clarke-Wright + ILS achievement (0.975 on hidden set), the
next priority was increasing the ILS iteration budget. The original 50
iterations completed in ~1s per instance, leaving plenty of headroom. This
eval increases to 150 iterations with a tighter deadline (0.90 instead of
0.95) and adds deadline checks in the local search and 2-opt loops.

## Result

| Metric | Eval 1 (50 iters) | Eval 5 (150 iters) | Delta |
|--------|--------------------|--------------------|-------|
| **Score** | **0.975020** | **0.979866** | **+0.00485** |
| Mean gap | +2.59% | +2.08% | -0.51% |
| Best gap | +0.05% | +0.02% (G100_1211_01) | -0.03% |
| Worst gap | +7.85% (G100_3344_01) | +7.16% (G100_3344_01) | -0.69% |
| Solved | 50 in 53.1s | 50 in 145.5s | +92.4s |

## Mechanism

More ILS iterations allow the solver to explore more diverse solutions. Each
iteration perturbs the best-known solution (or restarts with noisy Clarke-Wright)
and re-optimises with local search. With 3× the iterations, the solver finds
better solutions on most instances.

The deadline checks prevent any single instance from exceeding the 10s time
limit. The worst-case instance (G100_1312 on the dev set) took ~5s, well
within budget.

## What did not work

- **Or-opt in any form** — As documented in the eval-2 note, the Or-opt
  operator (segment relocation) was tried in three configurations and either
  timed out or regressed the score. It does not work for this problem at
  n=100 with a 10s time limit.

## Surprises / open questions

- G100_3344_01 remains the worst-gap instance at +7.16%, despite improving
  from 7.85%. This instance has a specific topology (clustered customers)
  that the Clarke-Wright + ILS pipeline struggles with.
- Several instances now have gaps below 0.5% (G100_1211, G100_1313, G100_2111,
  G100_2224, G100_3212, G100_3376). These are essentially solved.
- The total time (145.5s for 50 instances) is well within the 500s total
  budget (50 × 10s). The average per-instance time is ~2.9s.
- G100_2266_01 improved dramatically from +6.2% to +2.4%, suggesting the
  extra ILS iterations found a qualitatively different solution.

## Next

In descending expected payoff:

1. **Add Sweep algorithm construction** — Sort customers by polar angle
   around the depot, then assign to routes greedily. Combine with Clarke-Wright:
   try both constructions, keep the best. This gives a fundamentally different
   starting point that the ILS can build on. Expected: +0.002-0.005. Low risk.

2. **Adaptive perturbation** — Use a feedback mechanism: increase perturbation
   intensity when the solver stagnates (no improvement for N iterations),
   decrease when it finds improvements. Expected: +0.001-0.003.

3. **Run cross-exchange on every solution** — The 2-opt* operator never fires
   during local search because relocate and swap exhaust improvements. Try
   running it unconditionally as a post-processing step. Expected: +0.001-0.002.

4. **Add a third construction** — Farthest-insertion heuristic. Build routes
   by repeatedly inserting the farthest unvisited customer at the best
   position. Expected: +0.001-0.003.

## References

- [Eval 1: Clarke-Wright + ILS](eval-1-clarke-wright-ils.md) — the baseline
- [Eval 2-4: Or-opt failures](eval-2-or-opt-failures.md) — what did not work