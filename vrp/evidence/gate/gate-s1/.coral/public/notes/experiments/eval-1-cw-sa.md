---
creator: captain-nemo
created: 2026-07-14T13:16:31+00:00
commit: 6992311215e7
type: experiment
claim: "Clarke-Wright savings + SA with relocate/swap/2-opt achieves 0.962 on hidden instances (mean gap +3.96%)"
status: confirmed
confidence: high
evidence:
  attempt: 6992311215e7
  score_delta: '0.754 → 0.962 (public dev); 0 → 0.962 (hidden)'
  verified: true
based_on: []
touched:
  - solution.py
  - .claude/notes/research/cvrp-approaches.md
tags: [cvrp, sa, clarke-wright]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T13:17:28.456132+00:00'
---

# Eval 1: Clarke-Wright Savings + Simulated Annealing

**Score: 0.962** | Mean gap: +3.96% | 50 instances in 451.3s

## Context

First eval from the seed baseline. The seed solution was a simple nearest-neighbor greedy heuristic scoring ~0.754 on the public 10-instance dev set. This experiment implements a full CVRP solver with:
- Clarke-Wright savings algorithm (parallel version) for initial construction
- Nearest-neighbor as a fallback (keep the better of the two initial solutions)
- Intra-route 2-opt improvement on initial solution
- Simulated Annealing with inter-route relocate + swap + intra-route 2-opt operators
- Granular neighborhood restriction (Γ=30 closest customers)

## Result

| Metric | Seed (NN greedy) | This attempt | Delta |
|--------|-----------------|--------------|-------|
| Public dev score | 0.754 | 0.947 | +0.193 |
| Hidden instances score | N/A | **0.962** | — |
| Hidden instances mean gap | N/A | +3.96% | — |
| Best hidden gap | N/A | +0.19% (G100_1212_01) | — |
| Worst hidden gap | N/A | +9.04% (G100_3344_01) | — |
| Total time (50 instances) | N/A | 451.3s | — |

## Mechanism

1. **Clarke-Wright savings** provides a significantly better initial solution than nearest-neighbor. The parallel version merges the highest-savings route pairs first, producing routes with fewer crossing edges and lower total distance.

2. **Simulated Annealing** with three operators explores the solution space effectively:
   - **Relocate** (inter-route): Moves a customer to a different route. This is the most impactful inter-route operator for capacity-constrained problems.
   - **Swap** (inter-route): Exchanges two customers between routes. Helps when a relocate creates imbalance.
   - **2-opt** (intra-route): Removes crossing edges within a single route.

3. The SA cooling schedule (alpha=0.995, T0 ≈ avg_dist × 0.1) with 5000-stall limit allows the solver to use the full 10-second budget effectively.

4. Granular neighborhoods (Γ=30 closest customers) focus the search on promising moves, though the current implementation only uses them for choosing target routes in relocate.

## What Did Not Work

- **Per-iteration 2-opt random sampling**: The current approach picks random 2-opt moves rather than exhaustive search. This is slow to converge but works within the time budget. A more systematic 2-opt would be more efficient but harder to integrate with SA.

- **Non-improving stall counter at 5000**: This heuristic for detecting stagnation is crude. A better approach would use temperature-based restart or adaptive perturbation strength.

- **Single SA run**: The solver runs one long SA chain rather than multiple restarts. Multiple shorter runs could find better solutions.

## Surprises / Open Questions

- The worst-case gap is +9.04% on G100_3344_01. This is significantly higher than the best (+0.19%). The variance suggests the solver is inconsistent across instance types.

- The Clarke-Wright savings algorithm sometimes produces routes that violate capacity constraints in edge cases (demand at the boundary). The current implementation handles this correctly but the split in the savings computation may miss some feasible merges.

- The 2-opt* (cross-route exchange) operator is notably absent from the current implementation. Literature suggests it's the most important single operator for CVRP (Vidal et al., HGS paper).

## Next

1. **Add 2-opt* (cross-route exchange) operator** — This is the highest-impact addition. It exchanges the tail segments of two routes, which can fundamentally restructure the solution. Expected multiplier: +0.01-0.02 on score.

2. **Improve SA cooling/restart schedule** — The current 0.995 alpha is too slow. Consider a faster initial cool with re-heating, or multiple short runs. Expected multiplier: +0.005-0.01.

3. **Add VND (Variable Neighborhood Descent) intensification** — After SA, run a systematic VND that cycles through all operators until no improvement. Expected multiplier: +0.005-0.01.

4. **Add Or-opt operator** — Move sequences of 2-3 consecutive customers. Less important than 2-opt* but can help with specific instance structures.

## References

- [CVRP Solution Approaches](research/cvrp-approaches.md)
- Vidal (2020) — HGS with SWAP* neighborhood
- Clarke & Wright (1964) — Savings algorithm