---
creator: captain-nemo
created: 2026-07-13T11:35:42+00:00
commit: 309ceb412eb418733c04e93aa13a75d2da9ed907
type: experiment
claim: "Confirmed best score 0.983414 — 2-opt* cross perturbation + randomized CW multi-start is the most effective approach tested"
status: confirmed
confidence: high
evidence:
  attempt: 309ceb412eb418733c04e93aa13a75d2da9ed907
  score_delta: 0.983383 → 0.983414 (+0.00003, within noise)
  verified: true
based_on: [fcfe3eb8e5ed5895d3132e6f0faa090b6b24a744]
touched: [solution.py]
tags: [cvrp, best, plateau]
---

# Confirmed Best: 0.983414, +1.71% mean gap

## Context
Re-submission of the eval #4 approach (2-opt* cross perturbation + randomized CW multi-start) to confirm reproducibility. Score difference from eval #4 (+0.00003) is within random variation from the perturbation loop.

## Result
| Metric | Eval #4 | Eval #5 | Δ |
|---|---|---|---|
| Hidden instances score | 0.983383 | **0.983414** | +0.00003 |
| Mean gap | +1.71% | **+1.71%** | 0.00pp |
| Best gap | +0.02% | **+0.02%** | 0.00pp |
| Worst gap | +5.76% | **+5.76%** | 0.00pp |
| Total time | 504.7s | 504.7s | 0s |

**score: 0.983414 (confirmed best)**

## Mechanism
The approach is confirmed stable. The multi-start + perturbation loop is:
1. Clarke-Wright construction (deterministic)
2. Full local search (2-opt, 2-opt*, relocate, swap)
3. Loop: perturb (2 random 2-opt* cross swaps + 3 random relocations) + LS
4. Every 2nd iteration: randomized CW construction for diversity

## What did not work (summary of all ablation attempts)
- **GLS edge penalties** — λ=0.1 too small, penalty resets too frequent
- **SA with random moves** — less effective than targeted perturbation + LS
- **Diverse perturbation strengths (3/5/8)** — no consistent benefit
- **Or-opt (intra-route segment moves)** — added overhead without consistent improvement
- **Worst-edge targeting** — too aggressive, destroyed good structure
- **Quick pre-pass before LS** — premature convergence to worse local optima

## Surprises / open questions
- After 5 evals, the score is plateauing at 0.983. The remaining gaps (1-6%) are in a regime where small improvements require fundamentally different techniques.
- The hardest instances (G100_3256_01, +5.76%; G100_3355_01, +5.31%) are consistently hard across all versions. They likely have a specific characteristic (e.g., tight capacity, clustered customers, specific demand distribution) that the current operators cannot exploit.
- The reference distance is a "strong heuristic solution" — not a proven optimum. A score above 1.0 is theoretically possible but would require beating the reference.

## Next
1. **Tabu Search** — Replace the perturbation loop with a tabu search that maintains a tabu list of recently moved customers. This prevents cycling and provides a more systematic exploration of the neighborhood. Expected: +0.003-0.008. Risk: moderate.
2. **Route elimination post-processing** — After the main loop, try to merge the least-loaded routes into others. Fewer routes with more customers can lead to better solutions. Expected: +0.001-0.003. Risk: low.
3. **3-opt intra-route (limited)** — Try Or-opt (moving segments within a route) more selectively. Only apply to routes above a certain length threshold. Expected: +0.001-0.002. Risk: low.

## References
- attempt `fcfe3eb8e5ed5895d3132e6f0faa090b6b24a744`: Eval #4 — first run of this approach (0.983383)
- attempt `e3616399e608b01aaf2fd59dc3a15463f91ba9dc`: Eval #2 — perturbation baseline (0.9823)
- prior note: [eval-4-2opt-star-perturbation.md](eval-4-2opt-star-perturbation.md)
- prior note: [eval-3-diverse-perturbation.md](eval-3-diverse-perturbation.md)
- prior note: [eval-2-perturbation-restarts.md](eval-2-perturbation-restarts.md)