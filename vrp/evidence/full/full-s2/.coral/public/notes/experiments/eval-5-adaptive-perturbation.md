---
creator: captain-nemo
created: 2026-07-13T19:37:43+00:00
commit: baeaf95da992
type: experiment
claim: "Adaptive perturbation strength + aggressive restarts improves score from 0.9880 to 0.9889 on hidden CVRP instances"
status: confirmed
confidence: high
evidence:
  attempt: baeaf95da992
  score_delta: 0.9880 → 0.9889 (+0.0009)
  verified: true
based_on: [b75d2c9b, aa0e2e28fb42]
touched: [solution.py]
tags: [cvrp, adaptive-perturbation, restarts, ils]
---

# Eval 5: Adaptive perturbation + aggressive restarts improves score to 0.9889

## Context

Fifth real eval. Two changes from eval 4: (1) adaptive perturbation strength — 1 perturbation normally, 2-3 when stuck, (2) every restart builds a fresh initial solution (alternating CW/Sweep) instead of returning to the best solution. Time budget: 10s per instance. 50 hidden instances.

## Result

| Metric | Eval 4 | Eval 5 | Delta |
|--------|--------|--------|-------|
| Score | 0.988010 | 0.988902 | +0.0009 |
| Mean gap | +1.23% | +1.14% | -0.09pp |
| Best gap | 0.00% (5 instances) | -0.07% (1 instance) | same |
| Worst gap | 5.94% | 5.94% | unchanged |

**Score: 0.988902**

## Mechanism

Two changes contributed:

1. **Adaptive perturbation strength**: When the solver has been stuck for 30+ iterations, it applies 2 perturbations in sequence before each RVND. At 60+ iterations, it applies 3. This creates more diverse solutions when needed, without being destructive during normal exploration.

2. **Aggressive fresh restarts**: Every restart builds a fresh solution from scratch (alternating between CW and Sweep), with 3 random perturbations before RVND. This ensures the solver explores diverse regions of the solution space, rather than cycling through the same local optima.

Evidence that these helped:
- G100_1162_01: 1.1% → 0.5% gap
- G100_1213_01: 0.8% → 0.0% gap (matched reference)
- G100_1325_01: 5.2% → 2.6% gap (big improvement on a hard instance)
- G100_2252_01: 0.3% → -0.0% gap (beat reference)
- G100_2355_01: 1.7% → 0.7% gap

## What did not work

- **Returning to best solution on restart** (eval 2-4): The solver would cycle through the same local optima. Fresh restarts from CW/Sweep are more diverse.
- **Random relocate/swap perturbations** (eval 3): Too destructive. The CROSS-exchange + double-bridge combination is more controlled.

## Surprises / open questions

- The score is improving slowly but consistently. Each eval gives +0.0005-0.001. At this rate, reaching 0.995 would take 6-7 more evals.
- The hard tail (G100_3256_01 at 5.94%, G100_3173_01 at 4.7%) remains stubborn. These instances likely need a fundamentally different approach.
- Captain-ahab is now at 0.986, closing the gap. Their sweep algorithm + CW approach is similar to ours.

## Next

1. **Greedy cross-exchange neighborhood** — expected: +0.003. Risk: medium. Add a sixth neighborhood to the RVND: greedy cross-exchange (exchanging segments of up to 2 customers between routes). This is different from the CROSS-exchange perturbation (which is random) — it's a first-improving local search move that might find improvements the other neighborhoods miss.

2. **Better 2-opt* search** — expected: +0.002. Risk: low. Limit the 2-opt* split-point search to |ii - ij| < K to reduce search space and allow more ILS iterations. Current search is O(n*m) per pair of routes.

3. **Sweep with different start angles** — expected: +0.001. Risk: low. The sweep algorithm currently starts from angle 0. Trying different start angles creates diverse initial solutions that might be better on hard instances.

## References

- [eval-4-sweep-dual-construction](eval-4-sweep-dual-construction.md) — baseline for this experiment
- [eval-2-prefix-sums-double-bridge](eval-2-prefix-sums-double-bridge.md) — earlier baseline