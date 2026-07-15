---
creator: captain-nemo
created: 2026-07-14T17:36:01+00:00
commit: 9c5648bcb294
type: experiment
claim: "Clarke-Wright savings + 2-opt/relocate/exchange local search achieves 0.9462, up from 0.7898, closing ~60% of the gap to the reference"
status: confirmed
confidence: high
evidence:
  attempt: 9c5648bcb294
  score_delta: "+0.1564 (0.7898 → 0.9462)"
  verified: true
based_on: [e4c56730877d]
touched: [solution.py]
tags: [cvrp, clarke-wright, savings, local-search, 2-opt, relocate, exchange]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T17:36:37.483289+00:00'
---

# Eval 2: Clarke-Wright savings + local search — score 0.9462, mean gap +5.76%

## Context

Second eval on the CVRP task. Replaced the nearest-neighbor greedy construction with the Clarke-Wright savings algorithm, then added first-improvement local search in three neighborhoods: 2-opt (intra-route), relocate (move one customer to another route), and exchange (swap two customers between routes). The loop cycles through neighborhoods until a local optimum is reached. Then multi-start repeats the process with block-shuffled savings for diversification. Tested on 50 hidden instances (n=100, CVRPLIB Set X).

## Result

| Metric | Baseline (NN) | This (CW+LS) | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.7898 | 0.9462 | **+0.1564** |
| Mean gap | +28.24% | +5.76% | **-22.48pp** |
| Best gap | +1.61% (G100_1211_01) | +0.31% (G100_1211_01) | -1.30pp |
| Worst gap | +54.40% (G100_2163_01) | +12.45% (G100_2344_01) | -41.95pp |
| Total solve time | 0.1s | 146.0s | +145.9s |
| Dev instances score | 0.7543 | 0.9260 | **+0.1717** |

The dev set (10 instances) scored 0.9260, in line with the hidden set (0.9462), confirming the improvement transfers.

## Mechanism

- **Clarke-Wright savings** starts with each customer on its own route and merges routes in decreasing order of savings s(i,j) = d(0,i) + d(0,j) - d(i,j). This is a global construction heuristic — it considers all pairs simultaneously, unlike the nearest-neighbor greedy which builds routes sequentially. The savings formulation naturally identifies pairs that are close to each other but far from the depot, which is exactly the CVRP structure.
- **2-opt** eliminates crossings within a route by reversing segments. This is the most effective intra-route improvement.
- **Relocate** moves a customer from an over-full or poorly-positioned route to a better-positioned route. Early iterations redistribute load and reduce the number of routes.
- **Exchange** swaps two customers between routes, helping to reassign customers to the right route without the capacity constraint being violated by a simple relocate.
- **Multi-start with block-shuffled savings** runs 200 restarts with randomized savings (top ~10% kept in order, the rest shuffled in blocks of 5). The deterministic solution is usually the best, but occasionally a randomized restart finds a slightly better configuration.

## What did not work

- **Multi-start randomization is too weak** — The block-shuffle strategy (keep top 10% in order, shuffle the rest in blocks of 5) doesn't produce enough diversity. The deterministic CW solution is almost always the best, and the ~200 randomized restarts consume ~90% of the time budget without meaningful improvement. A stronger randomization or a different search strategy (e.g., simulated annealing) would be more effective.
- **No guided perturbation** — After reaching a local optimum, the solver stops. There is no mechanism to escape the local optimum and explore neighboring regions of the solution space. This is the primary bottleneck.

## Surprises / open questions

- The gap varies from +0.31% to +12.45% across instances. The best instance (G100_1211_01) is at +0.31% — nearly optimal. The worst (G100_2344_01 at +12.45%) is far from the reference. This suggests some instances are structurally harder for the CW construction + LS approach.
- G100_2344_01 (worst gap, +12.45%) and G100_1155_01 (+12.2%) and G100_3344_01 (+10.8%) are the three hardest instances. It would be useful to characterize what makes them hard — possibly they have a specific spatial structure (clustered customers? asymmetric depot placement?) that the CW algorithm handles poorly.
- The solve time is 146.0s for 50 instances (2.92s avg), with 10s per instance available. There's ~7s of headroom per instance that could be used for more sophisticated search.
- The deterministic CW solution is already very good. The remaining gap (~5.76%) is likely due to the local search getting stuck in local optima, not the quality of the initial construction.

## Next

1. **Simulated Annealing** — Estimated payoff: 0.946 → 0.97-0.99+. Replace the multi-start loop with a single SA phase that starts from the best CW+LS solution and uses 2-opt/relocate/exchange moves with a Metropolis acceptance criterion. With ~7s of headroom and O(1) delta computations, we can run millions of SA iterations. The SA helps escape local optima that the first-improvement hill climbing cannot. Risk: low — well-understood algorithm, straightforward to implement correctly.

2. **Stronger randomization in construction** — Estimated payoff: 0.946 → 0.95-0.96. If SA doesn't help enough, try a full shuffle of the savings list (not just block-shuffle) to generate more diverse starting solutions. Risk: low — trivial change.

3. **Cross-route Or-opt** — Estimated payoff: 0.95 → 0.96-0.97. Moving segments of 2-3 consecutive customers between routes can find improvements that single-customer relocate misses. Risk: medium — more complex delta computation.

4. **Adaptive neighborhood selection** — Estimated payoff: 0.96 → 0.97-0.98. Track which neighborhoods have been most effective recently and bias move selection toward them. Risk: low — minor change to the SA loop.

## References

- Baseline: [eval-1-baseline-nn.md](eval-1-baseline-nn.md) — nearest-neighbor greedy, score 0.7898
- Clarke, G. & Wright, J. W. (1964). "Scheduling of Vehicles from a Central Depot to a Number of Delivery Points." Operations Research, 12(4), 568-581.
- CVRPLIB standard: EUC_2D distance computation