---
creator: captain-nemo
created: 2026-07-14T20:25:33+00:00
commit: 21bb6a1d24c8
type: experiment
claim: "Multi-start CW+Sweep+GiantTour + RRT with 6 local search operators + cross-chain move + re-split + regret-2 improves CVRP score from 0.964 to 0.991"
status: confirmed
confidence: high
evidence:
  attempt: 21bb6a1d24c8
  score_delta: +0.027
  verified: true
based_on: [02a2699aa4c7, cd9399b9a62c, 4e1a5f566409]
touched: [solution.py]
tags: [vrp, record-to-record-travel, multi-start, local-search, cross-chain, re-split, regret-insertion]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T20:42:08.585363+00:00'
---

# Eval 8: Multi-start + RRT improves CVRP score from 0.964 to 0.991

## Context

Eighth attempt at the CVRP.  Previous best was 0.964 with guided LNS + reheat.
Studied captain-ahab's solution (0.993) to understand the key differences:
RRT metaheuristic, cross-chain move, re-split, regret-2 insertion, and
multi-start construction with 3 heuristics.

This experiment implemented all of these techniques.

## Result

| Metric | Previous (guided LNS) | Multi-start + RRT | Delta |
|---|---|---|---|
| Hidden set score (50 instances) | 0.9638 | 0.9905 | +0.0267 |
| Mean gap | 3.80% | 0.96% | -2.84% |
| Best gap | +0.13% (G100_1212_01) | -0.13% (G100_3374_01) | -0.26% |
| Worst gap | +11.41% (G100_1155_01) | +2.78% (G100_1262_01) | -8.63% |
| Total runtime | 405.2s | 490.1s | +84.9s |

**score: 0.9905** (hidden set, eval #8)

## Mechanism

- **Multi-start construction** generates 7-27 initial solutions using 3
  heuristics (Clarke-Wright, Sweep, Giant Tour + Split) with different
  parameter values, then picks the best after local search.
- **6 local search operators** (2-opt, Or-opt, relocate, exchange, 2-opt*,
  cross-chain) provide comprehensive neighbourhood coverage.  The cross-chain
  move (relocating 2-3 consecutive customers) fills a gap between relocate
  and 2-opt*.
- **Record-to-Record Travel (RRT)** accepts perturbed solutions within a
  deviation of the global best.  The deviation decreases from 5% to 0%.
- **Re-split** re-optimizes route assignment via shortest-path DP on the
  concatenated route ordering.
- **Regret-2 insertion** avoids greedy insertion's order-dependence.
- **Route removal strategy** removes entire routes for strong perturbation.

## What did not work

- **RRT is time-sensitive.**  Uses 9.8s per instance, leaving 0.2s margin.
- **G100_1262_01 (2.78%) is the worst.**
- **Multi-start uses ~3s**, leaving ~7s for RRT.  Could be tuned.

## Surprises / open questions

- **Score is 0.9905**, just 0.003 behind captain-ahab's 0.9933.
- **Cross-chain move is surprisingly effective.**
- **Some dev instances already achieve 1.0.**

## Next

1. **Tune RRT parameters** — expected payoff: +0.001-0.003.
2. **More construction iterations** — expected payoff: +0.001-0.002.
3. **Adaptive time budget split** — expected payoff: +0.001-0.002.

## References

- Prior eval: [eval-4-lns-ils.md](eval-4-lns-ils.md) — guided LNS scoring 0.952
- Prior eval: [eval-3-ils.md](eval-3-ils.md) — ILS scoring 0.949
- Prior eval: [eval-2-time-based-sa.md](eval-2-time-based-sa.md) — time-based SA scoring 0.946
- Prior eval: [eval-1-cw-sa.md](eval-1-cw-sa.md) — fixed-iteration SA scoring 0.943