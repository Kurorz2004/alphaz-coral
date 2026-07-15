---
creator: captain-ahab
created: 2026-07-14T10:00:00Z
commit: 2ae8c56a2788
type: experiment
claim: "Intra-route Or-opt adds negligible improvement (+0.0005) — need different approach for remaining gap"
status: refuted
confidence: medium
evidence:
  attempt: 2ae8c56a2788
  score_delta: "+0.0005"
  verified: true
based_on: [experiments/eval-2-ils-perturbation.md]
touched: [solution.py]
tags: [or-opt, diminishing-returns]
---

# Intra-route Or-opt: +0.0005 gain — essentially noise

## Context

Eval #2 (0.9869) used ILS perturbation + improvement-only acceptance. The next step was to add Or-opt (moving 2-3 customer segments within a route) — a classic intra-route operator that should catch improvements 2-opt misses.

## Result

**Score: 0.987454** (+0.0005 over eval #2, +0.0005 over eval #1 ILS).

| Metric | Before (eval #2) | After (eval #3) | Change |
|--------|------------------|-----------------|--------|
| Mean gap | +1.33% | +1.28% | -0.05pp |
| Best gap | -0.10% | 0.00% | lost beating reference |
| Worst gap | +3.93% | +5.07% | +1.14pp regression |

G100_3344 regressed from +2.6% to +5.07%. The Or-opt implementation is likely buggy.

## Mechanism

The Or-opt delta computation is complex and error-prone. The nested loops with "break" statements don't cleanly handle the case where the route is modified during iteration. The observed regressions suggest the implementation sometimes produces worse routes, which the LS can't fully repair.

## What did not work

- **Or-opt with manual delta computation** — The delta computation for Or-opt requires tracking edges at both the removal point and the insertion point simultaneously. The implementation in `_or_opt_route` is too complex and likely has edge-case bugs.
- **Iterating over a modified route** — The function modifies `route[:]` during iteration, which invalidates the loop bounds. The `break` statements try to handle this but don't fully succeed.

## Surprises / open questions

- **Or-opt should work in theory** — Moving 2-3 customer segments is a proven operator for TSP/CVRP. The failure here is in the implementation, not the concept. A cleaner implementation (e.g., don't actually modify the route during the scan, just compute delta and apply once) would be needed.
- **Gains are truly diminishing** — The gap has gone from 34% → 2.56% → 1.33% → 1.28%. Each step is smaller. The next breakthrough needs a fundamentally different approach, not a minor operator addition.

## Next

In descending order of expected payoff:

1. **Sweep algorithm construction heuristic** — Sort customers by polar angle around the depot and build routes radially. This is a completely different solution structure from CW. Interleaving sweep and CW restarts in Phase 1 should explore genuinely different basins. Expected: +0.002 to +0.005. Risk: low.

2. **Better ILS perturbation** — Replace greedy re-insertion with random insertion (insert at a random feasible position). This is more disruptive and helps escape deep local minima. Expected: +0.001 to +0.003. Risk: low.

3. **Simulated Annealing in Phase 2** — Accept worsening solutions with probability exp(-delta/T). This is the standard metaheuristic for escaping local optima. Expected: +0.001 to +0.005. Risk: medium (temperature tuning).

4. **Remove buggy Or-opt** — Revert the Or-opt addition to avoid the regressions it caused. Expected: no score change, but cleaner code. Risk: very low.

## References

- [experiments/eval-2-ils-perturbation.md](experiments/eval-2-ils-perturbation.md)
- Sweep algorithm: Gillett & Miller, "A Heuristic Algorithm for the Vehicle Dispatch Problem" (1974)