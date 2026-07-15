---
creator: captain-nemo
created: 2026-07-13T21:00:00
commit: 8736a4b122e9
type: experiment
claim: "Iterated Local Search (ILS) with Clarke-Wright + Sweep + NN construction, 2-opt + relocate + exchange + 2-opt* local search, and random swap perturbation (3-5 strength) achieves 0.9874 score on hidden CVRP instances"
status: confirmed
confidence: high
evidence:
  attempt: 8736a4b122e9
  score_delta: "0.754 → 0.9874 (+0.233)"
  verified: true
based_on: []
touched: [solution.py]
tags: [vrp, ils, local-search, 2-opt, clarke-wright]
---

# ILS for CVRP: 0.9874 score with Clarke-Wright + 2-opt + perturbation

## Context

Implemented an Iterated Local Search (ILS) solver for the CVRP problem (n=100
customers, 10s time limit per instance). The solver builds an initial solution
from the best of three construction heuristics, then alternates between local
search (2-opt, relocate, exchange, 2-opt*) and random perturbation to escape
local optima. Best score on hidden set: 0.9874 (commit 8736a4b1).

## Result

**Best score: 0.987354** (mean ref/dist over 50 hidden instances)

| Metric | Value |
|--------|-------|
| Mean gap | +1.30% |
| Best gap | +0.04% (G100_1211_01) |
| Worst gap | +5.94% (G100_3256_01) |
| Total time | 450.3s (50 instances) |
| Per-instance time | ~9.0s |

Performance on dev instances (10 instances):
| Metric | Value |
|--------|-------|
| Score | 0.9886 |
| Mean gap | +1.16% |
| Best gap | +0.00% (G100_2325_01) |
| Worst gap | +2.99% (G100_3133_01) |

## Mechanism

The solver uses a three-phase approach:

1. **Construction**: Try three heuristics (Clarke-Wright savings, Sweep
   algorithm sorted by polar angle, Nearest-Neighbor greedy) and pick the
   best initial solution. This gives a strong starting point.

2. **Local search**: Apply 2-opt (intra-route), relocate (move customer
   between routes), exchange (swap customers between routes), and 2-opt*
   (swap tails between routes) until no improvement is found.

3. **Iterated Local Search**: Perturb the current solution by randomly
   swapping customers between routes, then re-optimize. Accept only
   improving moves. Repeat until time limit is reached.

The 2-opt* implementation uses O(1) delta calculations to avoid expensive
full-route distance recomputation. The depot connections cancel out in the
delta formula, so only the split-point edges need to be compared.

## What did not work

- **Or-opt (moving segments within a route)**: The Or-opt operator was too
  slow due to O(n^3) complexity and while-loop convergence. It caused 9.5s+
  per instance without meaningful improvement. The limited version (single
  customer only) was fast but actually made solutions worse by destroying
  good route structure.

- **2-opt* with full distance computation**: The 2-opt* operator with full
  route distance recomputation was too slow (O(N^2 * M^2 * route_length)
  per call). The O(1) delta version is fast enough but rarely finds
  improvements that relocate + exchange don't already find.

- **Pure 2-opt without ILS**: The deterministic local search (without
  perturbation) plateaued at 0.935. The perturbations are what enable
  escaping local optima to reach 0.987.

- **Record-to-record travel**: Accepting worse solutions within a
  threshold helped some instances (G100_1356_01: 4.65% → 0.75%) but
  hurt others (G100_3133_01: 2.59% → 4.28%). The threshold is hard to
  tune across diverse instances.

- **VNS with systematic neighborhood sizes**: Increasing perturbation
  strength systematically (k*2 swaps) did not outperform the simple
  random perturbation approach.

- **Multi-start ILS**: Running multiple shorter ILS trajectories
  instead of one long one was worse because the local search doesn't
  converge fast enough (needs ~2s per convergence).

- **GRASP (randomized Clarke-Wright)**: Adding noise (±10%) to the
  savings values produced worse initial solutions, and the ILS couldn't
  recover. Score regressed from 0.9873 to 0.9863.

- **Destroy-and-repair perturbation**: Removing 3-9 customers and
  re-inserting them greedily was too aggressive (0.9735 vs 0.9825).

## Surprises / open questions

- The gap between dev and hidden scores (0.9886 vs 0.9874) suggests the
  dev set is slightly harder than the hidden set, or the ILS is
  overfitting slightly to the dev set.

- The worst instance (G100_3256_01 at 5.94%) consistently resists
  improvement. It may have a fundamentally different structure.

- The perturbation strength has a U-shaped effect: too weak (1-2 swaps)
  doesn't escape local optima, too strong (10+ swaps) destroys good
  structure. The sweet spot is 3-5 swaps.

- Different instances respond differently to the same perturbation.
  An adaptive approach might help.

## Next

1. **Adaptive perturbation**: Track which perturbation strengths work
   best during the search and adapt accordingly.

2. **Guided local search**: Penalize frequently-used edges to escape
   deep local optima.

3. **3-opt with limited search**: Only check 3-opt moves that are
   Or-opt-like (moving 1-2 customers). This is a local improvement
   that 2-opt might miss.

4. **Hybrid SA + ILS**: Use simulated annealing for the first half
   of the time budget (exploration), then ILS for the second half
   (exploitation).

## References

- Attempt: `coral show a904f58e1b37`
- Baseline attempt: `coral show HEAD~1` (0.754 score, nearest-neighbor
  greedy)