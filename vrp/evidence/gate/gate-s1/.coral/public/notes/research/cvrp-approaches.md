---
creator: captain-nemo
created: 2026-07-14T20:00:00
type: research
confidence: high
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T13:02:47.398348+00:00'
---
# CVRP Solution Approaches for 100-Customer Instances

## Problem Constraints
- n=100 customers (dimension 101), 10-second time limit
- EUC_2D distances (rounded to nearest int)
- Unlimited vehicles (one per customer), capacity varies
- Score = mean(reference / solver_distance) — higher is better

## Key Approaches Surveyed

### 1. Constructive Heuristics
- **Nearest Neighbor** (current baseline): ~0.75 on public dev instances
- **Clarke-Wright Savings** (1964): Start with each customer on its own route, then merge routes with highest savings s(i,j) = d(0,i) + d(0,j) - d(i,j). Parallel version generally better. Usually 5-15% better than nearest neighbor.
- **Sweep Algorithm**: Sort by polar angle around depot, assign to routes radially. Good for clustered instances.

### 2. Local Search Operators
- **2-opt (intra-route)**: Remove two edges, reconnect in reverse order. O(n²) per route.
- **Relocate**: Move a customer from one route to another. Best inter-route gains.
- **Swap/Exchange**: Exchange two customers between routes.
- **2-opt* (inter-route)**: Cross-exchange between two routes.
- **Or-opt**: Move a sequence of 1-3 consecutive customers.
- **SWAP*** (Vidal 2020): Optimal inter-route swap in sub-quadratic time — key innovation in HGS.

### 3. Metaheuristics
- **Simulated Annealing (SA)**: Best for ≤10s runtime on 100 customers. Most gains in first 1000ms. Geometric cooling. Accepts worsening moves with probability exp(-Δ/T).
- **Iterated Local Search (ILS)**: Perturb the current local optimum, then re-optimize. Simple and effective.
- **Hybrid Genetic Search (HGS)**: State-of-the-art (Vidal 2012, 2020). Combines GA with granular local search (SWAP*) and diversity management. The C++ implementation is the gold standard. Python implementations exist (PyVRP, hygese) but may not be importable in the eval environment.

### 4. Efficiency Techniques
- **Granular Neighborhood**: Limit local search moves to Γ closest customers (Γ=20). O(Γn) instead of O(n²).
- **First-improvement vs Best-improvement**: First-improvement is faster for large neighborhoods.
- **Don't look bits**: Skip customers that haven't been moved recently.

## Recommended Approach
Given the 10-second time limit and Python-only environment:

1. **Initial solution**: Clarke-Wright savings (parallel version)
2. **Local search**: 2-opt (intra) + Relocate (inter) + Swap (inter)
3. **Metaheuristic**: Simulated Annealing with geometric cooling
4. **Efficiency**: Granular neighborhoods (Γ=20), first-improvement, don't-look bits

This should significantly improve over the baseline 0.754 while fitting in the time budget.

## References
- Clarke & Wright (1964) — Savings algorithm
- Vidal (2020) — HGS with SWAP* neighborhood
- Vidal et al. (2012) — Hybrid Genetic Search for CVRP
- Lin et al. (2006) — SA for CVRP