---
creator: captain-nemo
created: 2026-07-14T06:45:00Z
commit: 534a5313c980
type: experiment
claim: "Multi-start construction (CW λ-savings + sweep) with best-of selection gives 0.966 from 0.955 CW-only baseline"
status: confirmed
confidence: high
evidence:
  attempt: 534a5313c980
  score_delta: "+0.011 from eval 1"
  verified: true
based_on: [8c5a24504389]
touched: [solution.py]
tags: [cvrp, clarke-wright, sweep, multi-start, local-search]
---

# Eval 2: Multi-start CW + Sweep + LS

Score: **0.965720** | Mean gap: +3.58% | Best gap: +0.18% | Worst gap: +8.07% | 50 instances in 32.1s

## Context

After the initial CW+LS baseline (0.955), added multi-start: 6 CW constructions with λ ∈ {0.7, 0.85, 1.0, 1.15, 1.3, 1.5} and 6 sweep constructions with 60° rotations. Each construction is locally optimized with 2-opt + relocate + exchange.

## Result

| Metric | Eval 1 (CW λ=1) | Eval 2 (Multi-start) | Delta |
|--------|-----------------|---------------------|-------|
| Score | 0.954850 | 0.965720 | **+0.0109** |
| Mean gap | +4.78% | +3.58% | **−1.2pp** |
| Worst gap | +9.74% | +8.07% | **−1.67pp** |
| Runtime (50 instances) | 6.4s | 32.1s | +25.7s |

## Mechanism

- **λ-savings**: Using λ < 1 emphasizes inter-customer distances (produces routes that follow natural clusters); λ > 1 emphasizes depot distances (produces more compact, radial routes). Different λ values explore different regions of the solution space.
- **Sweep algorithm**: Orders customers by polar angle from depot, then assigns greedily. Complements CW by providing a structurally different initial solution — CW merges nearest neighbors first, sweep groups by direction.
- **Best-of selection**: With 12 different starting points, at least one tends to be in a better basin after local search.

## What did not work

- **Simulated Annealing (attempted between eval 1 and eval 2)** — Random SA with relocate/exchange moves starting from a locally optimal solution destroyed the solution quality. The SA was too aggressive or the cooling schedule was wrong, resulting in score 0.838 (worse than the initial CW!). Abandoned SA approach for now — the issue was likely a combination of: (a) starting from a local optimum with no diversification, (b) incorrect delta computations, (c) temperature not tuned for this scale.
- **2-opt* cross-route operator** — Attempted implementation had edge case bugs. Properly implementing it correctly is complex.

## Surprises / open questions

- The solver uses only 32.1s / (50 × 10s) = 6.4% of the time budget. There's ~470s of unused time.
- Best gap is 0.18% — nearly optimal on one instance. This suggests CW+LS can find near-optimal solutions; the question is how to make it consistent.
- Worst gap 8.07% (G100_3344_01) — this instance has a tight capacity that may make the construction methods converge to poor basins.

## Next

1. **Iterated Local Search / Ruins-and-Recreate** — Use the remaining time budget. Starting from the best multi-start solution, apply ~20% customer reinsertion perturbations followed by LS. Repeat until deadline. *Expected: +0.01–0.02.*
2. **More constructions** — Add random greedy construction with shuffled customer order. *Expected: small marginal gain.*
3. **Proper 2-opt*** — Fix the cross-route operator implementation. *Expected: moderate gain.*
4. **Hybrid: ILS + VND** — Use Variable Neighborhood Descent (relocate → exchange → 2-opt*) inside the ILS loop. *Expected: moderate gain.*

## References

- [Eval 1 note](eval-1-cw-savings-baseline.md)
- Attempt 8c5a24504389 (CW+LS baseline)
- Attempt 534a5313c980 (this eval)
