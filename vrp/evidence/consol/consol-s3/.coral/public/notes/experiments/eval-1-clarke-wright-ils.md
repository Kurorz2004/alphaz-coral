---
creator: captain-nemo
created: 2026-07-15T04:15:00
commit: d5a5c37a23189eb57a3a56347ccb7588d9e9a534
type: experiment
claim: "Clarke-Wright savings + Iterated Local Search (multi-operator) scores 0.975 on the hidden 50-instance CVRP set, up from ~0.75 baseline"
status: confirmed
confidence: high
evidence:
  attempt: d5a5c37a23189eb57a3a56347ccb7588d9e9a534
  score_delta: 0.221
  verified: true
based_on: []
touched: [solution.py]
tags: [cvrp, clarke-wright, ils, local-search]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T21:12:17.047172+00:00'
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T21:12:17.047172+00:00'
---

# Eval 1: Clarke-Wright savings + ILS achieves 0.975 on hidden CVRP set

## Context

This was the first eval on the captain-nemo branch. The seed solution was a simple greedy nearest-neighbor heuristic scoring ~0.754 on the dev set. The task is CVRP with n=100 customers, EUC_2D distances, 10s time limit per instance.

## Result

| Metric | Value |
|--------|-------|
| **Score** | **0.975020** |
| Mean gap | +2.59% |
| Best gap | +0.05% (G100_1211_01) |
| Worst gap | +7.85% (G100_3344_01) |
| Solved | 50 instances in 53.1s |
| Dev set score | 0.965 (10 instances) |

Dev set breakdown (Clarke-Wright + 2-opt only, before ILS): 0.930. After adding ILS with 50 iterations: 0.965. The real eval score was slightly higher (0.975) than dev, suggesting the hidden instances are slightly easier or the ILS benefits them more.

## Mechanism

Three components contribute to the result:

1. **Clarke-Wright savings algorithm** — the core constructive heuristic. Each customer starts on its own route; savings s(i,j) = d(0i)+d(0j)-d(ij) are sorted descending; routes are merged greedily when capacity allows. This alone beats the greedy nearest-neighbor baseline by ~0.18 (0.754 → 0.930).

2. **Multi-operator local search** — after construction, alternating rounds of:
   - **Relocate**: move a single customer to a better position in another route
   - **Swap**: exchange two customers between routes
   - **2-opt\*** (cross-exchange): break two routes and reconnect crosswise
   - **Intra-route 2-opt**: reverse segments within a single route

3. **Iterated Local Search (ILS)**: 50 iterations alternating between:
   - **Noisy Clarke-Wright restarts** (every 3rd iteration): add uniform noise to savings values before sorting
   - **Perturbation** (other iterations): remove ~15% of customers and greedily reinsert them at best position

   After each perturbation/restart, full local search is applied. The best solution across all iterations is kept.

## What did not work

- **Cross-exchange (2-opt\*)**: The cross-exchange operator never triggered in practice — the relocate and swap moves already exhausted all improving moves before cross-exchange was tested. This is likely because the routes are already well-structured after Clarke-Wright construction, and cross-exchange only helps when routes have crossing patterns that other operators can't fix. It may be worth testing with a different search order or with a threshold-accepting variant.

- **Deterministic Clarke-Wright alone**: Without the ILS perturbation loop, the score plateaued at 0.930. The ILS iterations added ~0.035 to the score.

- **Pure noise-based restarts**: Restarting from scratch with noisy savings was less effective than perturbing the current best solution. The best improvement came from perturbing the best-known solution and re-optimizing.

## Surprises / open questions

- The dev set score (0.965) was slightly lower than the real eval (0.975), which is a good sign — the hidden instances respond well to the same approach.
- The worst gap instance (+7.85% on G100_3344_01) suggests there are structural patterns the Clarke-Wright + ILS pipeline struggles with. The instance with the largest gap likely has a specific topology (e.g., clustered customers) that the savings algorithm handles poorly.
- Cross-exchange (2-opt\*) never fired during local search. This may be a search-order issue — relocate and swap are tested first and exhaust the improving moves. Running cross-exchange on every solution regardless of local optimum might still find good moves.
- The ILS runs are fast (~1s per instance), leaving ~9s of time budget unused per instance.
- G100_1312_01 (capacity=5, very tight) nearly matches the reference at 0.99% gap with 20 routes. The savings algorithm handles tight-capacity instances well.

## Next

In descending expected payoff:

1. **Add Or-opt (segment relocation) to local search** — moving sequences of 2-3 consecutive customers can find improvements that single-customer relocate misses. Expected: +0.005-0.01. Low risk, easy to implement.

2. **Increase ILS iterations or add adaptive perturbation** — the current 50 iterations complete in ~1s, leaving ~9s unused. Can run 200+ iterations or use a more aggressive perturbation schedule. The key question is whether more iterations find better solutions or just converge. Expected: +0.002-0.005.

3. **Add GUIDED Local Search or tabu search** — use penalty-based diversification to escape deep local optima. Expected: +0.005-0.015. Higher risk, more complex.

4. **Replace Clarke-Wright with a different construction** — try the Sweep algorithm (polar angle sort around depot) or a farthest-insertion construction. Different constructions give different starting points. Expected: +0.002-0.005.

5. **Add 3-opt intra-route** — more powerful than 2-opt for the loose-capacity instances (where the gap is still 5-9%). High risk due to O(n³) complexity.

## References

- No prior notes exist — this is the captain-nemo branch's first eval.