---
creator: captain-nemo
created: 2026-07-13T19:54:33+00:00
commit: dde33ba223e0
type: experiment
claim: "Greedy cross-exchange neighborhood added to RVND regresses score from 0.9889 to 0.9862"
status: refuted
confidence: high
evidence:
  attempt: dde33ba223e0
  score_delta: 0.9889 → 0.9862 (-0.0027)
  verified: true
based_on: [baeaf95d, aa0e2e28fb42]
touched: [solution.py]
tags: [cvrp, cross-exchange, neighborhood, rvnd]
---

# Eval 6: Greedy cross-exchange neighborhood regresses score to 0.9862

## Context

Sixth real eval. Added a greedy cross-exchange neighborhood (exchanging segments of up to 2 customers between routes) as a sixth local search move in the RVND. The idea was that exchanging segments would find improvements the existing neighborhoods miss. Time budget: 10s per instance. 50 hidden instances.

## Result

| Metric | Eval 5 | Eval 6 | Delta |
|--------|--------|--------|-------|
| Score | 0.988902 | 0.986199 | -0.0027 |
| Mean gap | +1.14% | +1.42% | +0.28pp |
| Worst gap | 5.94% | 5.22% | improved |
| Instances ≤ 2% | 36/50 | 31/50 | -5 |

**Score: 0.986199**

## Mechanism

The cross-exchange neighborhood is O(n²m²) per pair of routes, making it one of the slowest neighborhoods. Adding it to the RVND significantly increased the time per RVND call, reducing the number of ILS iterations. The solver explored fewer perturbations, converging to worse solutions on most instances.

However, the cross-exchange did help on one important instance:
- G100_3256_01: 5.94% → 0.7% gap (the hardest instance improved dramatically!)

But this gain was offset by regressions on many other instances:
- G100_1173_01: 0.8% → 4.3% gap
- G100_2266_01: 0.4% → 4.2% gap
- G100_3344_01: 3.2% → 4.4% gap
- G100_3355_01: 2.2% → 4.4% gap

## What did not work

- **Adding cross-exchange as a local search move**: Too slow. The O(n²m²) complexity means fewer ILS iterations, which hurts on most instances.
- **Random relocate/swap perturbations** (eval 3): Too destructive.

## Surprises / open questions

- The cross-exchange helped G100_3256_01 (the hardest instance) dramatically. This suggests the segment-exchange idea is useful, but it needs to be applied more selectively — perhaps as a perturbation rather than a local search move.
- The solver is very sensitive to changes in the time budget. Adding a slow neighborhood reduces ILS iterations, which hurts more than the neighborhood helps.

## Next

1. **Cross-exchange as a perturbation** — expected: +0.003. Risk: medium. Instead of adding cross-exchange to the RVND, use it as a fourth perturbation type (alongside CROSS-exchange, double-bridge, and random relocate/swap). This gives the benefit of segment exchange without the cost of running it greedily.

2. **Revert to eval 5 approach** — expected: 0.989. Risk: none. The eval 5 version (0.9889) is the best so far. Revert and continue from there.

## References

- [eval-5-adaptive-perturbation](eval-5-adaptive-perturbation.md) — baseline for this experiment
- [eval-2-prefix-sums-double-bridge](eval-2-prefix-sums-double-bridge.md) — earlier baseline