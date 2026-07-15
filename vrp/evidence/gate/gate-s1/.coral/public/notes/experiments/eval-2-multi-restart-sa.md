---
creator: captain-nemo
created: 2026-07-14T13:41:07+00:00
commit: 5ee090367031
type: experiment
claim: "Multiple SA restarts with perturbation improves score from 0.962→0.976 on hidden instances (mean gap +2.46% vs +3.96%)"
status: confirmed
confidence: high
evidence:
  attempt: 5ee090367031
  score_delta: '0.962 → 0.976 (hidden); 0.947 → 0.975 (public dev)'
  verified: true
based_on: [6992311215e7]
touched:
  - solution.py
tags: [cvrp, sa, multi-restart, perturbation]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T13:41:44.049019+00:00'
---

# Eval 2: Multiple SA Restarts with Perturbation

**Score: 0.976** | Mean gap: +2.46% | 50 instances in 451.3s

## Context

Second eval, building on the Clarke-Wright + SA approach from eval 1. The key insight from the first eval was that the SA was cooling too fast (alpha=0.995, only ~1000 effective iterations before temperature drops to near-zero), then spending the remaining 8+ seconds executing random walk at effectively zero temperature. This meant the SA was a hill-climber for most of its runtime.

The fix: divide the time budget into 4 phases, each with a separate SA restart. Each restart:
- Starts from the best solution found so far (with perturbation)
- Uses a slightly different random temperature schedule (alpha 0.99-0.999, T0 weighted by random factor)
- Has its own reheat mechanism (when T < 0.5, reset to 0.3 * T0)
- The 2-opt* (cross-route) operator was also added

## Result

| Metric | Eval 1 (single SA) | Eval 2 (multi-restart) | Delta |
|--------|-------------------|----------------------|-------|
| Hidden instances score | **0.962** | **0.976** | +0.014 |
| Hidden mean gap | +3.96% | +2.46% | -1.50pp |
| Public dev score | 0.947 | 0.975 | +0.028 |
| Public dev mean gap | +5.69% | +2.54% | -3.15pp |
| Best hidden gap | +0.19% | +0.19% | — |
| Worst hidden gap | +9.04% | +7.33% | -1.71pp |
| Worst-case instance | G100_3344_01 | G100_2216_01 | — |

## Mechanism

1. **Multiple restarts escape local optima.** The single SA chain would get stuck in a basin and then just oscillate. By restarting from the best solution with perturbation (3-5 random relocate moves), the solver explores different regions of the search space.

2. **Restart-specific temperature schedule** provides better exploration. The randomized alpha (0.99-0.999) and T0 (0.8-1.2 * baseline) mean each restart explores at a different temperature profile, ensuring diverse search trajectories.

3. **Reheat mechanism** prevents the temperature from dropping to zero. When T < 0.5, it resets to 0.3 * T0, giving the SA a chance to escape local optima even within a single restart.

4. **2-opt* operator** adds cross-route exchange capability, allowing the solver to restructure routes more fundamentally than relocate/swap alone.

## What Did Not Work

- **The 2-opt* operator is expensive.** Computing tail sums for capacity checks is O(n) per move, and the operator only fires on 25% of iterations. Most 2-opt* moves are rejected due to capacity constraints. The net benefit is marginal — the score improvement is primarily from multiple restarts, not from 2-opt*.

- **VND was too expensive.** The earlier attempt at a full VND (Variable Neighborhood Descent) was O(n³) and burned time without improving the score.

- **G100_2216_01 remains hard at +7.33%.** This instance has a specific structure that resists the current operators. It may have tight capacity constraints or a specific customer distribution that makes route merging difficult.

## Surprises / Open Questions

- The worst-case dropped from +9.04% to +7.33%, but the new worst case (G100_2216_01) is different from the old one (G100_3344_01). This suggests the multi-restart approach helps different instances differently.

- G100_2245_01 is stuck at +4.08% across both evals, suggesting it's at a structural limit of the current operator set.

- The 2-opt* operator seems to add little value. The literature (Vidal, HGS paper) says it's the most important operator, but in a random SA context (vs. systematic local search), the benefit may be diluted.

## Next

1. **Remove 2-opt* operator** — It's expensive and doesn't help much. Removing it frees ~25% of SA iterations for more effective operators (relocate, swap, 2-opt). Expected multiplier: +0.002-0.005.

2. **Increase restarts and perturbation strength** — With 2-opt* removed, use 5-6 restarts instead of 4. Increase perturbation to 8-12 random moves across multiple operators. Expected multiplier: +0.003-0.008.

3. **Add quick VND post-processing after SA** — Run a single-pass best-improvement VND (relocate + swap + 2-opt) at the end. Only if time permits (1-2 seconds). Expected multiplier: +0.002-0.005.

4. **Adjust savings formula parameter** — Try λ (lambda) in the Clarke-Wright savings formula: s(i,j) = d(0,i) + d(0,j) - λ*d(i,j). λ > 1 may help for some instance types. Expected multiplier: +0.001-0.003.

## References

- [Eval 1: Clarke-Wright Savings + Simulated Annealing](experiments/eval-1-cw-sa.md)
- [CVRP Solution Approaches](research/cvrp-approaches.md)
- Vidal (2020) — HGS with SWAP* neighborhood
- Clarke & Wright (1964) — Savings algorithm