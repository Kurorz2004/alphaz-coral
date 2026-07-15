---
creator: captain-nemo
created: 2026-07-14T06:30:00Z
commit: 8c5a24504389
type: experiment
claim: "Clarke-Wright savings + local search (2-opt, or-opt, relocate, exchange) gives 0.955 score from a 0.754 nearest-neighbor baseline"
status: confirmed
confidence: high
evidence:
  attempt: 8c5a24504389
  score_delta: "+0.201 from baseline"
  verified: true
based_on: []
touched: [solution.py]
tags: [cvrp, clarke-wright, local-search, savings-algorithm]
---

# Eval 1: Clarke-Wright Savings + Local Search Baseline

Score: **0.954850** | Mean gap: +4.78% | Best gap: +0.18% | Worst gap: +9.74% | 50 instances in 6.4s

## Context

First attempt on this CVRP task. The seed solution was a naive nearest-neighbor greedy (score: 0.754). Replaced it with a Clarke-Wright parallel savings constructive heuristic followed by intra-route (2-opt, or-opt) and inter-route (relocate, exchange) local search.

## Result

| Metric | Baseline (NN-greedy) | This attempt | Delta |
|--------|---------------------|--------------|-------|
| Score | 0.754269 | 0.954850 | **+0.2006** |
| Mean gap | +34.29% | +4.78% | **−29.51pp** |
| Runtime (50 instances) | ~0s | 6.4s | +6.4s |

## Mechanism

- **Clarke-Wright savings** starts each customer on its own route and iteratively merges the highest-savings pairs. This produces much better initial routes than nearest-neighbor because it considers the global structure of the problem (savings from combining two customers onto the same route).
- **2-opt** reverses segments within a route to eliminate crossing edges.
- **Or-opt** moves 1-2 customer segments to better positions within the same route.
- **Relocate** moves a customer to a better position in a different route.
- **Exchange** swaps customers between routes — though this implementation likely has bugs in gain calculation, limiting its effectiveness.

## What did not work

- **Exchange operator gain calculation** — The gain computation for the exchange operator is complex and likely incorrect in some cases. It tries to compute exact deltas but the position tracking after removal-insertion is fragile. A simpler approach (full evaluation or more robust gain formulas) would be better.
- **2-opt in the current form** — Restarts from scratch after each improvement, which can lead to O(n³) worst-case behavior. A first-improvement strategy or more careful iteration would be faster.

## Surprises / open questions

- The Clarke-Wright heuristic alone (before local search) probably already beats the NN-greedy baseline substantially.
- Runtime is only 6.4s for all 50 instances — there's ~9.3s per instance available for metaheuristics.
- With 10s per instance and 100 customers, there's room for a substantial metaheuristic improvement.

## Next

1. **Simulated Annealing** — Biggest expected gain. Add SA with relocate/exchange/2-opt* moves on top of the Clarke-Wright + LS seed. With 9.3s of idle time per instance, we can run thousands of SA iterations. *Expected: ~0.97+*
2. **Fix exchange operator** — Simplify gain calculation or use full route cost evaluation. *Expected: small gain.*
3. **Add 2-opt* (cross-route)** — Swap the endings of two routes. Often effective for CVRP. *Expected: moderate gain.*
4. **Multiple restarts** — Run Clarke-Wright with different seed perturbations and pick the best. *Expected: small gain.*

## References

- [Clarke-Wright Savings Algorithm (1964)](https://pubsonline.informs.org/doi/abs/10.1287/opre.12.4.568)