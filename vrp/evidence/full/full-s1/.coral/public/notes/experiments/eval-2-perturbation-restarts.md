---
creator: captain-nemo
created: 2026-07-13T10:29:35+00:00
commit: e3616399e608b01aaf2fd59dc3a15463f91ba9dc
type: experiment
claim: "Perturbation-based restarts with Clarke-Wright + 2-opt/2-opt*/relocate/swap improve score from 0.9527 to 0.9823 (+0.0296)"
status: confirmed
confidence: high
evidence:
  attempt: e3616399e608b01aaf2fd59dc3a15463f91ba9dc
  score_delta: 0.9527 → 0.9823 (+0.0296)
  verified: true
based_on: [9ee0126151879a7765c6604fb23b011a88b9d825]
touched: [solution.py]
tags: [cvrp, perturbation, restarts, 2-opt-star, local-search]
---

# Perturbation-Based Restarts: 0.982301, +1.83% mean gap

## Context
Real-mode eval on 50 hidden CVRP instances (n=100). Built on the Clarke-Wright + local search from eval #1. Added 2-opt* (cross) inter-route operator and a perturbation-based restart loop: after reaching local optimum, randomly move 5 customers between routes, then re-optimize. Also tries a fresh Clarke-Wright construction every 5 restarts. Uses the full 10s time budget per instance.

## Result
| Metric | Eval #1 | Eval #2 | Δ |
|---|---|---|---|
| Hidden instances score | 0.952658 | **0.982301** | **+0.0296** |
| Mean gap | +5.03% | **+1.83%** | -3.20pp |
| Best gap | +0.23% | **+0.06%** | -0.17pp |
| Worst gap | +10.26% | **+6.57%** | -3.69pp |
| Total time (50 instances) | 10.8s | 503.8s | +493s |

**score: 0.982301**

## Mechanism
- **Perturbation-based restarts** are the primary driver of improvement. The first local search converges quickly to a local optimum. A random perturbation (move 5 customers to different routes) shakes the solution out of the local basin, and a second/third local search pass finds a different (and often better) local optimum. Over 10s this loop runs many times.
- **2-opt* (cross)** adds a qualitatively different move type: swapping suffixes between two routes. This can restructure the assignment of customers to routes in ways that relocate/swap cannot.
- **Fixed 2-opt delta bug** — the previous version had a bug in delta evaluation ((k+1) % len(best) wrapping to 0 instead of depot). Fixing this made 2-opt more effective.
- **Time utilization** — the solver now uses the full 10s per instance, vs 0.22s in eval #1. The marginal benefit of each additional restart decreases over time, but the total improvement is substantial.

## What did not work
- **λ-savings multi-start** — trying λ=0.6, 0.8, 1.0 and picking the best did not help. The local search converges to similar solutions regardless of λ. Multi-start added complexity without benefit.
- **First version of 2-opt* was too slow** — the initial implementation had a full `while improved` loop that cycled indefinitely. Adding iteration limits fixed it.
- **The relocate/swap previous implementation used full recomputation** — the eval #1 version recomputed `_total_distance` for every candidate move, which is O(n) per evaluation. The new version uses delta evaluation but still calls `_route_distance` for each candidate, which is a bottleneck.

## Surprises / open questions
- The solver now uses the full 10s time budget on every instance. This is a good thing — it means the perturbation loop is running until the deadline. But it also means we can't do more iterations without a more efficient implementation.
- Some instances converge much faster than others. G100_2325_01 (capacity 118) reached +0.21% gap quickly, while G100_3256_01 (capacity 98) still has +6.57% after 10s.
- The worst gaps are concentrated in specific capacity ranges (~80-120 capacity), suggesting the problem structure (moderate capacity, many routes) is harder for the current operators.
- 2-opt* is the most expensive operator (O(n²) per route pair). It might be worth running it less frequently or only on promising route pairs.

## Next
1. **Simulated Annealing / Record-to-Record Travel** — Replace the "perturb-and-reoptimize" loop with a proper SA metaheuristic that accepts worse moves with decaying probability. Expected: +0.005-0.015. Risk: moderate implementation complexity, more tuning parameters (cooling rate, iterations per temperature).
2. **Stronger perturbation** — Move 10-15 customers instead of 5, or use route-splitting as a perturbation (split a route in two and re-optimize). Expected: +0.002-0.005. Risk: low.
3. **Granular neighborhood search** — Restrict 2-opt* and relocate to nearby route pairs using a granularity threshold (e.g., only consider edges with distance < some factor of average). This could speed up the search and allow more iterations. Expected: +0.001-0.003. Risk: low.
4. **Or-opt (move contiguous segments)** — Move 2-3 consecutive customers between routes instead of just single customers. This can find improvements that single-customer relocate cannot. Expected: +0.003-0.008. Risk: moderate.

## References
- attempt `9ee0126151879a7765c6604fb23b011a88b9d825`: Eval #1 — Clarke-Wright + 2-opt/relocate/swap, the baseline for this work
- prior note: [eval-1-clarke-wright-local-search.md](eval-1-clarke-wright-local-search.md)