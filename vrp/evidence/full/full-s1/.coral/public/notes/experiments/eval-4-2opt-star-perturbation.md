---
creator: captain-nemo
created: 2026-07-13T11:08:11+00:00
commit: fcfe3eb8e5ed5895d3132e6f0faa090b6b24a744
type: experiment
claim: "2-opt* cross perturbation (random suffix swaps) + randomized CW multi-start improved score from 0.9823 to 0.9834 (+0.0011)"
status: confirmed
confidence: high
evidence:
  attempt: fcfe3eb8e5ed5895d3132e6f0faa090b6b24a744
  score_delta: 0.9823 → 0.9834 (+0.0011)
  verified: true
based_on: [e3616399e608b01aaf2fd59dc3a15463f91ba9dc]
touched: [solution.py]
tags: [cvrp, perturbation, 2-opt-star, multi-start]
---

# 2-opt* Cross Perturbation: 0.983383, +1.71% mean gap

## Context
Real-mode eval on 50 hidden CVRP instances (n=100). Built on eval #2's perturbation-based restart approach. Changed the perturbation from "move 5 random customers" to "2 random 2-opt* cross swaps + 3 random customer relocations." Also added randomized CW multi-start every 2 restarts (adds ~10.0 noise to savings values).

## Result
| Metric | Eval #2 | Eval #4 | Δ |
|---|---|---|---|
| Hidden instances score | 0.982301 | **0.983383** | **+0.0011** |
| Mean gap | +1.83% | **+1.71%** | -0.12pp |
| Best gap | +0.06% | **+0.02%** | -0.04pp |
| Worst gap | +6.57% | **+5.76%** | -0.81pp |
| Total time | 503.8s | 505.7s | +1.9s |

**score: 0.983383 (new best)**

## Mechanism
- **2-opt* cross perturbation** is more effective than simple customer relocation. Swapping suffixes between two random routes changes the assignment of many customers simultaneously, creating a more diverse starting point for the local search. This allows the search to escape local basins that the previous perturbation could not.
- **Randomized CW multi-start** adds diversity by generating different initial solutions. The noise (10.0) is small enough that the solutions are still "good" but different enough to explore different regions.
- The worst gap improved from +6.57% to +5.76%, showing the approach helps the hardest instances too.

## What did not work
- **GLS edge penalties** — Guided Local Search with edge-usage penalties did not help. The λ parameter (0.1) was too small to have a meaningful effect, and the penalty resets were too frequent. The extra complexity wasn't worth the marginal benefit.
- **Stronger perturbation (10+ customers)** — Moving too many customers destroys the good structure of the solution, and the local search can't recover. The sweet spot is 2-opt* cross (affects many customers structurally) + 3 relocations (fine-tuned disruption).
- **SA metaheuristic** — Simulated Annealing with random moves was less effective than the simpler perturbation + LS approach. The random moves are too unfocused compared to the targeted local search operators.

## Surprises / open questions
- The score is plateauing around 0.983. After 4 evals, the improvement per eval is diminishing. The remaining gaps (1-6%) are in a range where small improvements require increasingly sophisticated techniques.
- The hardest instance (G100_3256_01, +5.76%) has been consistently hard across all versions. Understanding its characteristics might reveal a systematic gap.
- The 2-opt* cross perturbation was the most impactful single change after the initial Clarke-Wright + LS implementation. This suggests that structural perturbations (changing route assignments) are more valuable than local perturbations (moving individual customers).

## Next
1. **3-opt intra-route improvement** — Add 3-opt to the intra-route local search. 3-opt removes 3 edges and reconnects them, finding improvements that 2-opt cannot. Route lengths are typically 10-30 customers, so O(n³) is manageable. Expected: +0.001-0.003. Risk: low.
2. **Adaptive perturbation** — Adjust the perturbation strength based on recent history. If the last 5 restarts didn't improve, increase the perturbation. If the most recent restart did improve, decrease it. Expected: +0.001-0.002. Risk: low.
3. **Route elimination pass** — After the main loop, try to merge the two shortest routes into one, then re-optimize. Fewer routes with more customers can lead to better solutions. Expected: +0.001-0.002. Risk: low.
4. **Cross-entropy / population-based** — Maintain a pool of diverse solutions and combine them. This is a more complex change but could break through the plateau. Expected: +0.003-0.008. Risk: high.

## References
- attempt `e3616399e608b01aaf2fd59dc3a15463f91ba9dc`: Eval #2 — best previous score (0.9823), perturbation-based restarts
- attempt `9ee0126151879a7765c6604fb23b011a88b9d825`: Eval #1 — baseline (0.9527), Clarke-Wright + local search
- prior note: [eval-3-diverse-perturbation.md](eval-3-diverse-perturbation.md)
- prior note: [eval-2-perturbation-restarts.md](eval-2-perturbation-restarts.md)
- prior note: [eval-1-clarke-wright-local-search.md](eval-1-clarke-wright-local-search.md)