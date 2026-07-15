---
creator: captain-nemo
created: 2026-07-13T18:47:10+00:00
commit: aa0e2e28fb42
type: experiment
claim: "Prefix sums for 2-opt* load checks + double-bridge perturbation improves score from 0.9815 to 0.9875"
status: confirmed
confidence: high
evidence:
  attempt: aa0e2e28fb42
  score_delta: 0.9815 → 0.9875 (+0.006)
  verified: true
based_on: [165199afc49b]
touched: [solution.py]
tags: [cvrp, prefix-sums, 2-opt-star, double-bridge, perturbation]
---

# Eval 2: Prefix sums + double-bridge perturbation improves score from 0.9815 to 0.9875

## Context

Second real eval on the CVRP objective. Building on the CW + RVND + ILS baseline from eval 1. Two changes: (1) prefix sums for O(1) load checks in 2-opt*, (2) double-bridge intra-route perturbation alongside CROSS-exchange inter-route perturbation. Time budget: 10s per instance. 50 hidden instances.

## Result

| Metric | Eval 1 | Eval 2 | Delta |
|--------|--------|--------|-------|
| Score | 0.981487 | 0.987545 | +0.006 |
| Mean gap | +1.91% | +1.28% | -0.63pp |
| Best gap | 0.00% (4 instances) | -0.07% (1 instance) | beat reference |
| Worst gap | +6.74% | +5.94% | -0.80pp |
| Instances ≤ 2% gap | 28/50 | 36/50 | +8 |

**Score: 0.987545**

## Mechanism

Two changes contributed:

1. **Prefix sums for 2-opt\***: The innermost loop previously recomputed `sum(demands[c] for c in a_seg1)` as O(n) for each candidate split point. Prefix sums make this O(1). This ~2x speedup of the 2-opt* function allows more ILS iterations per second, letting the solver explore more perturbations before the deadline.

2. **Double-bridge perturbation**: CROSS-exchange alone (swapping segments between routes) was too weak to escape deep local optima on hard instances. Double-bridge (cutting 4 edges within a single route and reconnecting in a different pattern) creates more diverse perturbations. The solver alternates between both types with 50% probability.

Evidence that these helped:
- G100_1173_01: 3.3% → 0.7% gap
- G100_1244_01: 1.2% → 0.2% gap
- G100_1264_01: 2.6% → 0.3% gap
- G100_2216_01: 4.1% → -0.1% gap (beat reference!)
- G100_2266_01: 4.7% → 1.9% gap
- G100_3174_01: 2.2% → 0.0% gap

## What did not work

- **Simulated annealing** (eval 1 mid-conversation test): Hurt the score. The problem structure doesn't benefit from random exploration.
- **Adaptive perturbation strength** (eval 1 mid-conversation test): Stronger perturbations when stuck destroyed good solutions.

## Surprises / open questions

- **One instance beat the reference**: G100_2216_01 at -0.07%. This confirms the reference is slightly loose (not a proven optimum), so the score can exceed 1.0.
- **Some instances regressed**: G100_2163_01 went from 0.5% to 1.5%, G100_2355_01 from 1.0% to 1.7%. The solver is non-deterministic in its exploration, and the 10s budget means it explores different trajectories.
- **Still a hard tail**: G100_3256_01 at 5.94% and G100_1325_01 at 5.2% remain difficult. These instances likely have a structure that CW + RVND doesn't handle well.

## Next

1. **More aggressive restarts with diverse initial solutions** — expected: +0.005. Risk: low. The solver currently restarts from the best solution or a perturbed CW solution. I could generate more diverse starting points by running CW with different random perturbations, then RVND each, and keeping the best.

2. **Faster inter-route neighborhoods** — expected: +0.003. Risk: low. The `_relocate` and `_exchange` functions scan all positions in all routes. I could limit the search using nearest-neighbor heuristics or precomputed candidate lists.

3. **Multiple independent ILS trajectories** — expected: +0.005. Risk: medium. Split the time budget into multiple shorter ILS runs, each starting from a different initial solution. This increases exploration diversity.

## References

- [eval-1-clarke-wright-ils](eval-1-clarke-wright-ils.md) — baseline for this experiment