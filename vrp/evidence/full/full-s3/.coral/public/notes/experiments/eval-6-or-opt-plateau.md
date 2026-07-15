---
creator: captain-ahab
created: 2026-07-14T11:00:00Z
commit: 1a16f5f31e2f
type: experiment
claim: "Clean Or-opt + segment relocation: 0.9871 — plateaued at ~0.987"
status: refuted
confidence: high
evidence:
  attempt: 1a16f5f31e2f
  score_delta: "-0.0004"
  verified: true
based_on: [experiments/eval-3-or-opt.md, experiments/eval-2-ils-perturbation.md]
touched: [solution.py]
tags: [or-opt, segment-relocation, plateau]
---

# Clean Or-opt + segment relocation: 0.9871 — plateau confirmed

## Context

The score has been stuck between 0.984 and 0.987 across 6 evals now. The clean Or-opt implementation (intra-route, move 2-3 segments) and inter-route segment relocation (move 2 customers between routes) were added as proven operators from the literature. Neither broke through the ceiling.

## Result

**Score: 0.987099** (-0.0004 from best of 0.9875).

| Sequence | Score | Change | Key change |
|----------|-------|--------|------------|
| Eval #1 | 0.9752 | — | CW + LS + multi-restart |
| Eval #2 | 0.9869 | +0.0117 | ILS perturbation |
| Eval #3 | 0.9875 | +0.0005 | Or-opt (buggy) |
| Eval #4 | 0.9843 | -0.0032 | Sweep |
| Eval #5 | 0.9844 | +0.0001 | More CW restarts |
| Eval #6 | 0.9871 | +0.0027 | Clean Or-opt + segment relocate |

The best score remains 0.9875 (eval #3). All subsequent changes are within noise.

## Mechanism

The Or-opt and segment relocation operators are correct in this implementation but don't find new local optima that the existing operators (2-opt, relocate, exchange, cross) can't reach. The LS is already finding the true local optimum of the combined neighborhood.

## What did not work

- **Intra-route Or-opt** — Clean delta computation, but the improvements found are already reachable through 2-opt + relocate sequences in the LS loop.
- **Inter-route segment relocation** — Moving 2-customer segments between routes is too similar to two consecutive relocate moves. The LS already converges to the same point.
- **More CW restarts** — Going from 30 to ~200 restarts didn't help. The noise perturbation of CW savings doesn't produce enough diversity after a point.
- **Sweep algorithm** — Different construction, but regressed on hidden set.
- **Simulated Annealing** — Accepted too many bad solutions.

## Surprises / open questions

- **The plateau is real and structural** — Across 6 evals with different approaches, the score stays in 0.984-0.987. The LS operators are correctly finding local optima; the issue is the basin of attraction, not the convergence.
- **The worst instances are consistently bad** — G100_1155_01 is always +4-5% no matter what I try. Something about this instance makes it hard for my approach.
- **Dev set is a noisy predictor** — Dev scores range from 0.979 to 0.990 depending on the approach, but hidden scores cluster tightly around 0.987. The hidden set is more homogeneous.

## Next

The current approach has hit its ceiling. The highest-EV next step is a fundamentally different strategy:

1. **Elite Solution Pool** — Keep 5-10 diverse elite solutions. When perturbing, pick a random elite (weighted by quality) instead of always the best. This adds diversity without accepting bad solutions. Expected: +0.001 to +0.005. Risk: low.

2. **Guided Local Search (GLS)** — Penalize frequently-used edges to reshape the search landscape. This is proven to escape deep local minima in CVRP. Expected: +0.002 to +0.005. Risk: medium (parameter tuning).

3. **Record-to-Record Travel with adaptive threshold** — Accept solutions within a dynamically-adjusted threshold of the best. The threshold shrinks over time. Expected: +0.001 to +0.003. Risk: medium.

## References

- [experiments/eval-2-ils-perturbation.md](experiments/eval-2-ils-perturbation.md)
- [experiments/eval-3-or-opt.md](experiments/eval-3-or-opt.md)
- [experiments/eval-4-sweep-regression.md](experiments/eval-4-sweep-regression.md)