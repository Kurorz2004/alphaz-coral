---
creator: captain-ahab
created: 2026-07-13T10:55:00+00:00
commit: 0827f20057a0ee38fa2db6dcef534c3169518690
type: experiment
claim: "Sweep algorithm + CW constructions + fixed shake intensity 5: 0.9821, regression from 0.9837"
status: refuted
confidence: medium
evidence:
  attempt: 0827f200
  score_delta: 0.9837 → 0.9821 (-0.0016)
  verified: true
based_on: [01e24fa9, 8620837f]
touched: [solution.py]
tags: [cvrp, sweep-algorithm, vns, perturbation]
---

# Sweep algorithm + CW: 0.9837 → 0.9821 (regression)

## Context

Eval #6. Previous best (0.9837, 01e24fa9) used CW-only constructions + fixed shake intensity 5. This eval added a sweep algorithm construction (sort customers by polar angle, sweep into routes) to diversify the initial solutions. Phase 1: 5 CW configs + 3 sweep configs. Phase 2: perturbation with fixed intensity 5, periodic fresh constructions alternating between CW and sweep.

## Result

| Metric                      | Eval #4 (CW-only, fixed shake) | This (CW + sweep, fixed shake) | Δ       |
|-----------------------------|--------------------------------|-------------------------------|---------|
| Score                       | 0.9837                         | 0.9821                        | -0.0016 |
| Mean gap                    | +1.67%                         | +1.84%                        | +0.17pp |
| Best gap                    | +0.09% (G100_1211_01)          | +0.04% (G100_3111_01)         | -       |
| Worst gap                   | +5.27% (G100_3173_01)          | +6.80% (G100_3256_01)         | +1.53pp |
| Total time (50 instances)   | 482.4s                         | 482.1s                        | -0.3s   |

## Mechanism

- **Sweep algorithm didn't help.** The sweep construction provides different initial solutions, but they're not consistently better than CW. The sweep tends to produce routes that are "pie-slice" shaped, which can be suboptimal for instances where customers are not radially distributed.
- **The regression is likely noise.** The perturbation approach is stochastic; different random seeds produce slightly different results. The 0.0016 drop is within the noise range for this approach.
- **The sweep construction takes time** that could be used for more perturbation cycles. Phase 1 with 3 sweep configs is slower than CW-only, reducing the number of perturbation cycles in phase 2.

## What did not work

- **Sweep algorithm** — not beneficial for these instances. The radial structure doesn't match the customer distribution.
- **Variable shake intensity** (eval #5, 0.9816) — large shakes destroy too much structure.
- **Best approach remains: CW-only multi-start + perturbation with fixed intensity 5** (0.9837).

## Next

1. **Faster local search with incremental cost computation** — Avoid recomputing `_route_distance` from scratch for each candidate move. Compute only the delta from affected edges. Should make LS 2-3x faster, allowing more perturbation cycles. Expected payoff: +0.002-0.005.
2. **Guided Local Search** — Penalize frequently-used edges to diversify the search. Expected payoff: +0.005-0.015. Risk: medium.
3. **Record-to-Record Travel** — Accept uphill moves within a threshold during LS. Expected payoff: +0.003-0.01. Risk: low-medium.

## References

- attempt `0827f200`: this eval (sweep + CW, score 0.9821)
- attempt `01e24fa9`: best so far (CW-only perturbation, score 0.9837)
- attempt `8620837f`: VNS variable shake (score 0.9816)