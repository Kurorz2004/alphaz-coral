---
creator: captain-ahab
created: 2026-07-14T20:15:43+00:00
commit: a7ac765a42fdcdb2bff0b3ed2fd216ff55f8103b
type: experiment
claim: "Multi-start Clarke-Wright + Sweep + Giant-Tour construction with 6-operator local search and Record-to-Record Travel metaheuristic achieves 0.9933 score on CVRP n=100 hidden instances"
status: confirmed
confidence: high
evidence:
  attempt: a7ac765a42fdcdb2bff0b3ed2fd216ff55f8103b
  score_delta: "0.754 → 0.993; +0.239"
  verified: true
based_on: [baseline]
touched: [solution.py]
tags: [cvrp, clarke-wright, sweep, giant-tour, rrt, local-search]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T20:16:18.109554+00:00'
---

# CVRP solver: Multi-start CW + Sweep + Giant Tour + RRT — score 0.9933

## Context
CVRP n=100, 10s time limit per instance, 50 hidden instances. The baseline was a simple nearest-neighbor greedy (score 0.754). This attempt implements a comprehensive solver with:
- **3 construction heuristics**: Clarke-Wright Savings (varied λ + noise), Sweep algorithm (polar angle), Giant Tour + Split (route-first cluster-second)
- **6 local search operators**: 2-opt, Or-opt, Relocate, Exchange, 2-opt*, Cross-chain move
- **Record-to-Record Travel metaheuristic**: destroy & repair + accept within deviation threshold

## Result
| Metric | Baseline | This | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.754 | 0.993 | +0.239 |
| Mean gap | +34.29% | +0.68% | -33.61pp |
| Best gap | — | -0.13% (G100_3374_01) | — |
| Worst gap | +50.66% | +2.91% (G100_3355_01) | — |
| Solved instances | 10/10 dev | 50/50 hidden | — |

**score: 0.9933**

## Mechanism
- **Clarke-Wright with λ sweep (0.6, 0.8, 1.0, 1.2, 1.4)** covers different route shapes: low λ creates more direct (hub-and-spoke) routes, high λ creates more circuitous routes with higher savings. The multi-start finds the best basin.
- **Noisy savings (up to 25% perturbation)** and **sort-order noise** provide diverse initial solutions without changing the algorithm structure.
- **Sweep algorithm** complements Clarke-Wright by constructing routes based on polar angle — useful for geographically clustered instances where CW's savings-based merging is suboptimal.
- **Giant Tour + Split** provides a third construction paradigm: TSP-first, then split into capacity-feasible routes via shortest-path. This is especially effective for tight-capacity instances where CW and Sweep both struggle.
- **6-operator local search** covers all standard CVRP neighborhoods: 2-opt (intra-route reversal), Or-opt (intra-route chain move), Relocate (single customer move), Exchange (two-customer swap), 2-opt* (cross-route tail exchange), Cross-chain (2-3 customer move between routes).
- **2-opt* optimization**: precomputing cumulative tail loads reduced complexity from O(n^3) to O(n^2), making it feasible for instances with 20+ routes.
- **Record-to-Record Travel**: destroy 10-40% of customers, re-insert via greedy or regret-2, run local search, accept if within 3%→0% deviation of best. This provides strong diversification while maintaining solution quality.
- **Three perturbation strategies** (random, worst-edge removal, route removal) cycle across RRT iterations, providing diverse neighborhood structures.

## What did not work
- **LNS (Large Neighborhood Search) in early version** — destroyed too many customers (30-50%) and re-inserted naively, causing capacity violations and duplicate customers. The root cause was a shallow-copy bug in `_lns_improve` where `surviving_routes` shared inner lists with the original routes, causing corruption. After fixing the bug, the LNS was still not improving because it consumed too much time without enough benefit.
- **Guided Local Search (GLS)** — penalizing edges in the current solution and re-optimizing with augmented distances. The penalty mechanism was too aggressive and caused the search to diverge from good solutions. The augmented distance matrix distorted the problem enough that the local search found worse solutions when evaluated with original distances.
- **Fixed wall-clock time budget for multi-start** — using `_time.time() < deadline` as the primary loop control made results non-deterministic across runs. Switching to fixed iteration counts (50 random restarts, 1000 RRT iterations) with time checks as a safety net improved determinism.

## Surprises / open questions
- **G100_3355_01 at 2.91% gap** is the worst instance by far. The next-worst is 2.5%. This instance likely has a specific structure (tight capacity with many routes) where the 3 construction heuristics all produce poor initial solutions that the RRT can't escape.
- **G100_3374_01 beat the reference (-0.13%)** — the reference is a "strong heuristic" not a proven optimum, so beating it is possible. The solver found a genuinely better route arrangement.
- **The sweep algorithm helps some instances but hurts others.** On the dev set, adding sweep improved G100_3133_01 (2.69%→2.13%) but made G100_2245_01 slightly worse (0.01%→0.41%). The 3-construction hybrid approach averages out the risk.
- **2-opt* optimization was critical** — the original O(n³) tail-load computation was the bottleneck for instances with 20+ routes. The O(n²) version runs 10-100x faster on these instances.
- **The 2.91% gap on the worst instance** suggests there's a structural issue (likely a tight-capacity instance where all routes are at capacity and inter-route operators can't find improvements). The RRT perturbation is the only mechanism for changing route assignment, and it might not be strong enough.

## Next
1. **Targeted perturbation for tight-capacity instances** — For instances where routes are at capacity (total demand ≈ routes × capacity), the RRT perturbation needs to be more aggressive. Try: (a) higher destroy_pct (40-50%), (b) regret-3 insertion, (c) biased removal that targets routes with least slack. Expected payoff: +0.002-0.005. Risk: might hurt easy instances.
2. **Route re-optimization via split** — After the RRT phase, apply a "re-split" procedure: concatenate all routes into a super-route, then re-split using the shortest-path algorithm. This re-optimizes the route assignment without changing the customer ordering. Expected payoff: +0.001-0.003. Risk: low.
3. **Adaptive operator selection** — Track which operators (2-opt, relocate, etc.) find improvements most frequently and run them more often. This is especially useful for instances where only intra-route operators are effective. Expected payoff: +0.001-0.002. Risk: moderate complexity.
4. **Instance-specific time allocation** — Reserve more time for hard instances (e.g., those with tight capacity) and less for easy ones. The current solver uses a fixed 10s per instance, but some instances converge in 4-5s. Expected payoff: +0.001-0.002. Risk: low.

## References
- baseline attempt (b5d065b): initial nearest-neighbor greedy solver, score 0.754
- All code changes in `solution.py` at commit a7ac765a42fdcdb2bff0b3ed2fd216ff55f8103b