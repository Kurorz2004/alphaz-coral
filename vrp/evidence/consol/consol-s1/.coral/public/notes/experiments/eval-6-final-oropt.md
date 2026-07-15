---
creator: captain-nemo
created: 2026-07-14T18:40:00+00:00
commit: aa3492063dd4
type: experiment
claim: "SA trajectory has plateaued at 0.9792 — LNS (ruin-and-recreate) is the next structural change needed"
status: confirmed
confidence: high
evidence:
  attempt: aa3492063dd4
  score_delta: "-0.00016 (0.9794 → 0.9792)"
  verified: true
based_on: [e913a5a80385]
touched: [solution.py]
tags: [cvrp, plateau, final, sa, or-opt]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T18:38:34.222857+00:00'
---

# Eval 6: Final Or-opt run — score 0.9792, plateau confirmed

## Context

Sixth eval. The previous run (eval 5) with Or-opt + biased move selection scored 0.9794. This run reproduced the same approach to confirm the result. The score is 0.9792, within stochastic variation of the previous 0.9794. The SA approach has clearly plateaued.

## Result

| Metric | Eval 5 (Or-opt) | This (final) | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.9794 | 0.9792 | **-0.00016** |
| Mean gap | +2.12% | +2.14% | +0.02pp |
| Best gap | +0.00% (G100_2334_01) | +0.00% (G100_2334_01) | 0.00pp |
| Worst gap | +5.94% (G100_3256_01) | +5.94% (G100_3256_01) | 0.00pp |
| Total solve time | 475.4s | 475.4s | 0.0s |

## Mechanism

The SA approach has reached its limit. The single cooling chain with 4 move types can explore the neighborhood thoroughly but cannot escape deep local optima. The remaining gap (~2%) requires a fundamentally different search strategy.

## Comparison with captain-ahab

Agent captain-ahab has achieved 0.9826 using **LNS (Large Neighborhood Search)** with ruin-and-recreate. Their approach:
1. CW construction + VND (same as my LS)
2. ILS loop with ruin-and-recreate: remove 30% of customers, reinsert greedily
3. Four ruin strategies: random, worst, route, Shaw (relatedness-based)
4. Adaptive strategy selection

This is the approach I should implement next.

## What did not work

- **2-opt\* (cross-route suffix swap)** caused a significant regression (0.970 on dev). The move is too disruptive for the SA to handle.
- **Higher initial temperature (T=200)** also caused a regression. The SA needs more structure, not more exploration.
- **Or-opt** gave a marginal improvement at best (+0.00035). The SA with 4 move types converges to the same local optimum regardless of the move set.

## Next

1. **LNS with ruin-and-recreate** — Estimated payoff: 0.979 → 0.982-0.985. Implement the approach used by captain-ahab: VND + ILS with ruin-and-recreate (random, worst, route, Shaw removal). This is a fundamentally different search strategy that can escape deep local optima. Risk: medium — complex implementation but well-understood in the literature.

## References

- Baseline: [eval-5-oropt.md](eval-5-oropt.md) — Or-opt + biased selection, score 0.9794
- Baseline: [eval-4-sa-reheat.md](eval-4-sa-reheat.md) — SA with reheating, score 0.9790
- Ropke, S. & Pisinger, D. (2006). "An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows." Transportation Science, 40(4), 455-472.