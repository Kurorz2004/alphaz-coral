---
creator: captain-nemo
created: 2026-07-13T18:34:09+00:00
commit: 165199afc49b
type: experiment
claim: "Clarke-Wright + RVND + ILS with CROSS-exchange perturbation reaches 0.981 on 50 hidden CVRP instances"
status: confirmed
confidence: high
evidence:
  attempt: 165199afc49b
  score_delta: 0.9815 (baseline 0.0)
  verified: true
based_on: []
touched: [solution.py]
tags: [cvrp, clarke-wright, rvnd, ils, 2-opt, or-opt, relocate, exchange]
---

# Eval 1: Clarke-Wright + RVND + ILS reaches 0.981 on hidden instances

## Context

First real eval on the CVRP objective. Baseline was the seed solution — a naive nearest-neighbor greedy heuristic (score ~0.75 on dev). Implemented a full Clarke-Wright savings-based construction, 5 local search neighborhoods (2-opt, Or-opt, Relocate, Exchange, 2-opt*), and an Iterated Local Search with CROSS-exchange perturbation. Time budget: 10s per instance. Only numpy available.

## Result

| Metric | Baseline | Eval 1 | Delta |
|--------|----------|--------|-------|
| Score | 0.0 (no prior) | 0.981487 | +0.981 |
| Mean gap | — | +1.91% | — |
| Best gap | — | 0.00% (4 instances) | — |
| Worst gap | — | +6.74% (G100_3256_01) | — |

**Score: 0.981487**

## Mechanism

The improvement comes from three components working together:

1. **Clarke-Wright construction** is far better than nearest-neighbor (CW gives ~0.86 vs NN ~0.75 on dev). The savings-based merging builds natural clusters.
2. **RVND** with 5 neighborhoods (2-opt, Or-opt, Relocate, Exchange, 2-opt*) in a first-improving loop converges to a strong local optimum in ~0.3s.
3. **ILS with CROSS-exchange perturbation** escapes local optima — but the perturbation is weak (1-3 customer segments), so many iterations re-converge to the same local optimum.

The solver is compute-bound: each RVND call takes ~0.3s, limiting the ILS loop to ~30 iterations per instance. The `_two_opt_star` function is the bottleneck because it recomputes `sum()` for each candidate split point, making its innermost loop O(n) instead of O(1).

## What did not work

- **Simulated annealing acceptance** (mid-conversation test, not submitted): SA with adaptive temperature dropped dev score from 0.987 to 0.982. The solver accepted too many worse solutions, wasting iterations that could have been spent hill-climbing. The problem structure (integer distances, tight local optima) doesn't benefit from SA.
- **Adaptive perturbation strength** (multiple CROSS-exchange moves when stuck): Also hurt the score. Stronger perturbation destroyed good route structures without finding better ones.

## Surprises / open questions

- **4 instances solved to optimality** (0% gap): G100_1211_01, G100_1212_01, G100_2334_01, G100_3111_01. These are likely instances with well-clustered demands that CW handles naturally.
- **Worst gap is 6.74%** on G100_3256_01. The gap distribution is uneven: most are under 3%, but a few are 5-7%. This suggests the solver gets stuck in deep local optima on hard instances.
- The reference is close to optimal (within 1-2% of BKS on public instances), so 0.981 is a solid starting point — but there's room for improvement, especially on the hard tail.

## Next

1. **Prefix sums for 2-opt\* load checks** — expected: +0.005-0.01. Risk: low. The innermost loop calls `sum(demands[c] for c in a_seg1)` as O(n) — caching prefix sums makes it O(1). Should speed up local search 2-3x, allowing more ILS iterations.
2. **Double-bridge perturbation** — expected: +0.005-0.01. Risk: medium. CROSS-exchange with 1-3 customers is too weak. A double-bridge (4-opt) move cuts 4 edges and reconnects, creating more diverse solutions. Should help escape deep local optima.
3. **Multiple diverse initial solutions** — expected: +0.003-0.005. Risk: low. Run CW -> RVND, then repeat with randomized perturbation of the CW solution. Keep the best. Simple and doesn't require more time.

## References

- No prior notes — this is the first experiment on this objective.