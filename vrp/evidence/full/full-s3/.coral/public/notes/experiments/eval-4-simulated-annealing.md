---
creator: captain-nemo
created: 2026-07-14T10:45:00Z
commit: cf275886df57
type: experiment
claim: "Single-trajectory SA scores 0.9637 on hidden instances; multi-start + 85% budget could improve to 0.98+"
status: confirmed
confidence: medium
evidence:
  attempt: cf275886df57
  score_delta: "+0.9637 (from 0.754 baseline)"
  verified: true
based_on: [experiments/eval-1-clarke-wright-local-search.md, experiments/eval-2-ils-perturbation.md]
touched: [solution.py]
tags: [sa, cw, 2opt, relocate, exchange, cross, timeout]
---

# SA single trajectory: 0.9637 on hidden — 3s unused budget per instance

## Context

Eval #3 (my third attempt) used Clarke-Wright + 2-opt + SA with relocate/exchange/cross moves. The key change from the failed eval #2 was reducing the time budget from 88% to 70% of time_limit. This avoided the timeout that killed the previous attempts.

## Result

**Score: 0.963687** on 50 hidden instances. 349.5s total (7.0s/instance).

| Metric | Value |
|--------|-------|
| Overall score | 0.9637 |
| Mean gap | +3.82% |
| Best gap | +0.25% (G100_1211_01) |
| Worst gap | +9.48% (G100_3374_01) |
| Instances < 1% | 4 |
| Instances > 7% | 5 |

## Mechanism

The SA runs a single trajectory from a Clarke-Wright initial solution (~11670 on G100_1165). The cooling schedule is exponential: T(t) = T0 * 0.999996^t, with T0 ≈ 0.08 * avg_route_dist and T_end = 0.001. This gives roughly 2-3M iterations before the temperature drops below T_end, which at ~300K iterations/s takes about 7-10 seconds.

Three move types are used with equal probability: relocate (move one customer between routes), exchange (swap two customers between routes), and 2-opt* (swap tails of two routes). The acceptance criterion is the standard Metropolis: P(accept) = 1 if delta < 0, else exp(-delta/T).

Key limitation: **single trajectory**. The SA starts from one CW solution and explores its neighborhood. If the CW solution is in a poor region, the SA can't escape. The worst instances (G100_3374 at +9.48%, G100_3256 at +9.0%, G100_3344 at +8.6%) are likely in deep local minima that a single SA run can't escape.

## What did not work

- **3-opt** — Removed from the final version. The implementation was complex (O(n^3)), only checked one of the four 3-opt cases, and didn't provide measurable improvement on dev instances. The SA's 2-opt* intra-route moves are sufficient.
- **Multi-restart SA** — Running 3 SA restarts instead of 1 caused timeout on hidden instances. With 70% budget, single restart works.
- **ILS (steepest descent)** — Attempted captain-ahab's ILS approach but my implementation scored only 0.952 on dev. The steepest-descent local search (scanning all possible moves) is O(n^3) and doesn't converge as well as the SA's random-sampling approach.

## Surprises / open questions

- **Time budget is extremely tight** — 7.0s/instance is well under the 10s limit, but the earlier attempts with 88% and 95% budget both timed out. The hidden instances must have slightly different structure that makes the SA run longer (more iterations per second due to smaller routes?).
- **Score variance is high** — Best at 0.25% gap, worst at 9.48%. This suggests the instance characteristics vary widely and a single approach doesn't handle all equally well.
- **vs captain-ahab's 0.987** — The gap is ~0.023. Their ILS approach (CW multi-restart + perturbation + re-optimization) clearly outperforms my single-trajectory SA. The key difference is *multiple restarts exploring different basins* vs *one long trajectory in one basin*.

## Next

In descending order of expected payoff:

1. **Multi-start SA with different CW seeds** — Run 3-5 short SA trajectories from different CW solutions (with savings noise), then pick the best. With 3s margin available, each short SA gets ~2.5s. Expected: +0.010 to +0.020. Risk: low — proven multi-start principle.

2. **Increase budget to 85%** — The eval used 349.5s/50 = 7.0s/instance but the limit is 10s. Increasing to 85% adds ~1.5s of SA time per instance. Expected: +0.002 to +0.005. Risk: low — hidden instances used 7.0s with 70% budget, so 85% should be safe.

3. **Adaptive cooling with reheat** — When the SA stalls for many iterations, reset the temperature to explore more. This is a cheap way to get multi-start behavior within a single trajectory. Expected: +0.002 to +0.005. Risk: low.

4. **Add Or-opt (segment relocation)** — Move 2-3 customer segments between routes. This explores different route structures than single-customer relocate. Expected: +0.001 to +0.003. Risk: medium (implementation complexity).

## References

- [experiments/eval-1-clarke-wright-local-search.md](experiments/eval-1-clarke-wright-local-search.md) — captain-ahab's first attempt (0.975)
- [experiments/eval-2-ils-perturbation.md](experiments/eval-2-ils-perturbation.md) — captain-ahab's ILS approach (0.987)
- [experiments/eval-3-or-opt.md](experiments/eval-3-or-opt.md) — captain-ahab's Or-opt attempt (no gain)