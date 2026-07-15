---
creator: captain-nemo
created: 2026-07-14T17:18:05+00:00
commit: e4c56730877d
type: experiment
claim: "Nearest-neighbor greedy heuristic achieves 0.7898 on the hidden 50-instance set, leaving substantial room for improvement via Clarke-Wright savings + local search"
status: confirmed
confidence: high
evidence:
  attempt: e4c56730877d
  score_delta: "0.7898 (no prior baseline)"
  verified: true
based_on: []
touched: [solution.py]
tags: [cvrp, baseline, greedy, nearest-neighbor]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T17:18:30.628440+00:00'
---

# Eval 1: Nearest-neighbor greedy baseline — score 0.7898, mean gap +28.2%

## Context

First eval on the CVRP task. The provided seed solution is a pure greedy nearest-neighbor heuristic that builds one route at a time by always picking the closest feasible customer. No improvement phase. No randomization. Tested on 50 hidden instances (n=100, CVRPLIB Set X).

## Result

| Metric | Value |
|---|---|
| Score (mean ref/dist) | 0.7898 |
| Mean gap | +28.2% |
| Best gap | +1.6% (G100_1211_01) |
| Worst gap | +54.4% (G100_2163_01) |
| Total solve time | 0.1s (all 50 instances) |
| Dev instances score | 0.7543 |

The dev set (10 instances) scored 0.7543, slightly lower than the hidden set (0.7898), suggesting the hidden instances are slightly easier for this baseline.

## Mechanism

- **Greedy nearest-neighbor** builds routes that are locally optimal but globally poor. It commits to early customers without considering the impact on later route construction.
- The algorithm never revisits a route after building it — no intra-route or inter-route improvement.
- On instances with tight capacity (e.g., capacity=5, G100_1312_01), the greedy approach is relatively closer to the reference (dev gap +6.5%) because the capacity constraint forces short routes regardless of the heuristic.
- On instances with ample capacity, the greedy approach performs poorly (dev gaps up to +50.6%) because it can chain many customers in a suboptimal order without any cross-route optimization.
- Solve time is negligible (0.1s for 50 instances) — there is massive headroom to spend on more sophisticated algorithms.

## What did not work

- **No alternative approaches tested yet** — this is the first eval, establishing the baseline. The nearest-neighbor is the seed solution provided.

## Surprises / open questions

- The gap varies enormously by instance (1.6% to 54.4%). This suggests some instances are structurally easier (customers clustered near the depot? favorable capacity/demand ratios?) while others are much harder. It would be useful to characterize which instances are hard.
- The dev set score (0.7543) is lower than the hidden set (0.7898), meaning the dev set is harder for this algorithm. This is useful — improvements on the dev set should translate to the hidden set.
- With 10 seconds per instance and n=100, we can afford computationally expensive algorithms. The baseline uses 0.002s per instance — we have 5000x more time available.

## Next

1. **Clarke-Wright savings algorithm** — Estimated payoff: 0.79 → 0.88-0.92. This is the single most impactful change. The savings algorithm is known to significantly outperform nearest-neighbor for CVRP construction. Expected to close roughly half the gap to the reference. Implement with 2-opt intra-route improvement. Risk: low — well-understood algorithm, straightforward to implement correctly.

2. **Local search (2-opt + relocate + exchange)** — Estimated payoff: 0.88 → 0.93-0.97. After construction, apply first-improvement hill climbing in multiple neighborhoods. This is standard and effective. Risk: low — needs careful implementation to avoid O(n³) per iteration.

3. **Multi-start / GRASP** — Estimated payoff: 0.93 → 0.97-1.00+. Run the construction + local search many times with randomized savings to explore different regions of the solution space. With 10 seconds, we can afford many restarts. Risk: medium — needs careful randomization to avoid converging to the same local optimum.

## References

- Seed solution: `solution.py` at commit e4c56730877d
- CVRPLIB standard: EUC_2D distance computation
- Clarke, G. & Wright, J. W. (1964). "Scheduling of Vehicles from a Central Depot to a Number of Delivery Points." Operations Research, 12(4), 568-581.

## Predictions backfilled

**Clarke-Wright savings (item 1):** Predicted 0.79 → 0.88-0.92 (CW + 2-opt). Actual: 0.79 → 0.9462 (CW + 2-opt + relocate + exchange + multi-start). The actual score exceeded the upper bound of the prediction because the local search was more effective than expected (all three neighborhoods, not just 2-opt). The CW alone likely achieves ~0.88-0.90, and the LS adds the rest.

**Local search (item 2):** Predicted 0.88 → 0.93-0.97. Actual: achieved 0.9462, which is within the predicted range. The combination of 2-opt, relocate, and exchange is effective.

**Multi-start / GRASP (item 3):** Predicted 0.93 → 0.97-1.00+. Actual: 0.9462, below the lower bound. The block-shuffle randomization was too weak to produce meaningful diversity. This prediction needs updating — a stronger randomization or a different search strategy (e.g., SA) is needed to reach the 0.97+ range.