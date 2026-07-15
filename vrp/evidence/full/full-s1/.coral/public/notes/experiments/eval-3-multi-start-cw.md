---
creator: captain-ahab
created: 2026-07-13T10:13:00+00:00
commit: d22f81fed216527f26443de6b9eb735fd3e75573
type: experiment
claim: "Multi-start CW with randomized savings (noise + λ sweep) + local search improves score from 0.9527 to 0.9723"
status: confirmed
confidence: high
evidence:
  attempt: d22f81fe
  score_delta: 0.9527 → 0.9723 (+0.0196)
  verified: true
based_on: [5dfa4f44, 9ee01261]
touched: [solution.py]
tags: [cvrp, multi-start, clarke-wright, randomized-savings, lambda-sweep]
---

# Multi-start CW: 0.9527 → 0.9723, mean gap +2.87%

## Context

Eval #2. Previous eval (5dfa4f44) used deterministic CW + full local search and scored 0.9527, plateauing at the same level as captain-nemo's simpler approach (9ee01261, 0.9527). The plateau suggested the deterministic construction always converges to the same local optimum. Added multi-start with randomized savings (noise = 0.1-0.3 × uniform(-1,1)) and λ-sweep (0.6-1.3) to generate diverse initial solutions, then pick the best after local search.

## Result

| Metric                      | Eval #1 (solo CW + LS) | This (multi-start CW + LS) | Δ       |
|-----------------------------|------------------------|-----------------------------|---------|
| Score                       | 0.9527                 | **0.9723**                  | +0.0196 |
| Mean gap                    | +5.03%                 | +2.87%                      | -2.16pp |
| Best gap                    | +0.18% (G100_1211_01)  | +0.03% (G100_1211_01)       | -0.15pp |
| Worst gap                   | +14.31% (G100_3376_01) | +7.16% (G100_1155_01)       | -7.15pp |
| Total time (50 instances)   | 6.7s                   | 459.5s                      | +452.8s |
| Time per instance           | 0.13s                  | 9.19s                       | +9.06s  |

**score: 0.9723**

Instance-level improvements (selected):
- G100_3376_01: 14.31% → 1.4% (huge gain from different construction)
- G100_1162_01: 4.2% → 1.6%
- G100_1211_01: 0.18% → 0.03% (near-optimal)
- G100_1256_01 (hidden): +9.9% → +4.7%

## Mechanism

- **Multi-start with randomization** is the key driver. The deterministic CW construction converges to a single local optimum. By adding noise to the savings values and sweeping λ, we generate structurally different initial solutions that land in different basins of attraction. The local search then climbs each basin, and we pick the best.
- **λ-savings** (savings = d(0,i) + d(0,j) - λ·d(i,j)) controls route shape. λ < 1 favors merging distant customers (fewer, longer routes); λ > 1 favors geometric proximity (more, tighter routes). Sweeping λ = 0.6-1.3 covers both regimes.
- **Noise** (savings *= 1 + noise_scale * uniform(-1,1)) scrambles the merge order slightly, producing different solutions without changing the overall structure.
- **Time budget is now the binding constraint.** 459.5s/500s total means ~9.2s/instance. The solver does 5 config restarts + as many random restarts as fit in the remaining time (~2-3 extra).
- The worst gap dropped from 14.3% to 7.2%, confirming that the deterministic construction was catastrophically bad on some instances.

## What did not work

- **The random restarts hit diminishing returns.** After the first 5 configs (which are diverse by design), additional random restarts find similar or worse solutions. The probability of a random restart beating the best of 5 diverse configs is low.
- **Time management is inefficient.** The `while` loop for random restarts runs until 90% of time budget, then the last iteration may take 2+s and overshoot. Some instances may hit the 10s hard limit.
- **No escape from local optima during LS.** Each restart still converges to a single local optimum. If the construction is in a bad basin, the LS climbs to that basin's local optimum and stays there. A perturbation mechanism (shake + restart) would help after convergence.

## Surprises / open questions

- **The best gap is 0.03%** — essentially optimal on one instance. This confirms the reference distances are achievable (they're not proven optima, but close).
- **Time is now the bottleneck.** The previous eval used 6.7s total; this one uses 459.5s. The marginal cost of each additional restart is ~1.5-2s. We can't afford many more restarts without either (a) making the LS faster or (b) reducing the number of restarts.
- **Captain-nemo tried perturbation-based restarts** (e3616399, pending score). This is a similar idea but differs in mechanism — perturbation shakes the solution after LS rather than randomizing the construction. If it scores well, it confirms the basin-escape hypothesis.
- **The worst gaps are now 6-7% on 2-3 instances.** These are likely cases where the optimal solution requires a specific structure (e.g., few routes with high load) that the CW construction fundamentally can't produce.

## Next

1. **Granular Neighborhood Search (GNS)** — Precompute k-nearest neighbors (k=20-30) and restrict local search to moves involving only neighbor customers. This should make each LS iteration 2-5x faster, allowing more restarts per time budget. Expected payoff: +0.005-0.015 (from more restarts). Risk: low — well-studied technique.
2. **Perturbation + VNS** — After LS converges, shake the solution (randomly relocate 5-10 customers) and run LS again. Repeat until time runs out. This is more efficient than full restarts because it preserves good structure. Expected payoff: +0.01-0.02. Risk: medium — may need tuning of shake intensity.
3. **Faster local search with caching** — Cache route distances and incremental delta computations to avoid recomputing from scratch. Expected payoff: +0.0-0.005 (speed only). Risk: low.
4. **Route minimization** — Post-process to merge routes where feasible, reducing route count and opening up better inter-route moves. Expected payoff: +0.003-0.01. Risk: low.

## References

- attempt `d22f81fe`: this eval (multi-start CW, score 0.9723)
- attempt `5dfa4f44`: previous eval (deterministic CW + LS, score 0.9527)
- attempt `9ee01261` (captain-nemo): CW + basic LS, score 0.9527
- attempt `e3616399` (captain-nemo, pending): perturbation-based restarts
- prior note: [eval-1-clarke-wright-local-search.md](eval-1-clarke-wright-local-search.md) — captain-nemo's analysis of the CW plateau
- prior note: [eval-2-captain-ahab-cw-plus-local-search.md](eval-2-captain-ahab-cw-plus-local-search.md) — my previous note on the plateau