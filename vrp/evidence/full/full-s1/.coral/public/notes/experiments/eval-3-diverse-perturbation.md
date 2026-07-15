---
creator: captain-nemo
created: 2026-07-13T10:50:04+00:00
commit: 5e12e2298b986f5d5697aa3e7ca21409101774bf
type: experiment
claim: "Diverse perturbation strengths (3/5/8 customers) + quick pre-pass before full LS slightly regressed hidden score from 0.9823 to 0.9804"
status: refuted
confidence: high
evidence:
  attempt: 5e12e2298b986f5d5697aa3e7ca21409101774bf
  score_delta: 0.9823 → 0.9804 (-0.0019)
  verified: true
based_on: [e3616399e608b01aaf2fd59dc3a15463f91ba9dc]
touched: [solution.py]
tags: [cvrp, perturbation, ablation]
---

# Diverse Perturbation: 0.980448 (regression of -0.0019)

## Context
Real-mode eval on 50 hidden CVRP instances (n=100). Built on eval #2's perturbation-based restart approach. Made three changes: (1) vary perturbation strength across restarts (3/5/8 customers), (2) add a quick 2-opt+relocate pre-pass before full LS, (3) more frequent fresh CW constructions (every 2 restarts instead of 5). Aim was to do more iterations per time budget.

## Result
| Metric | Eval #2 | Eval #3 | Δ |
|---|---|---|---|
| Hidden instances score | 0.982301 | **0.980448** | **-0.0019** |
| Mean gap | +1.83% | **+2.02%** | +0.19pp |
| Best gap | +0.06% | **+0.01%** | -0.05pp |
| Worst gap | +6.57% | **+6.90%** | +0.33pp |
| Total time | 503.8s | 504.1s | +0.3s |

**score: 0.980448 (regressed)**

## Mechanism
- The quick pre-pass (2-opt + relocate before full LS) was intended to speed convergence, but it may have pushed the search into a different local basin that the full LS couldn't escape from. The full LS operators (2-opt*, swap) are designed to find different improvements than 2-opt + relocate — running them AFTER a pre-pass means they have less to work with.
- The diverse perturbation strengths had mixed effects: some instances improved (G100_1356_01 went from +5.77% to +2.70% on public), but others regressed (G100_1312_01 went from +1.43% to +2.43% on public).
- The public instance improvements did not generalize to the hidden instances, suggesting the hidden set has different characteristics.

## What did not work
- **Quick pre-pass** — Running 2-opt + relocate before the full LS may have prematurely converged to a local optimum. The full LS should start from the raw perturbation, not from a partially-improved state.
- **Diverse perturbation strengths** — Varying between 3, 5, and 8 customers didn't help. The perturbation strength of 5 (from eval #2) was already a good balance between exploration and exploitation.
- **More frequent CW constructions** — Every 2 restarts instead of 5. This may have been too frequent, wasting time on CW solutions that are no better than the perturbed ones.

## Surprises / open questions
- The public and hidden instances have different characteristics. The diverse perturbation helped on public (0.9816 vs 0.9759) but hurt on hidden (0.9804 vs 0.9823). This is a reminder to not overfit to the public set.
- The best gap reached +0.01% (nearly optimal) on one hidden instance, but the worst gap increased to +6.90%. The approach is becoming more unpredictable.
- 3 evals in, the score is plateauing around 0.98. A fundamentally different approach may be needed to break through.

## Next
1. **Guided Local Search (GLS)** — Add edge-usage penalties to the perturbation loop. After each local search, penalize edges that appear in the solution. The augmented distances encourage exploring different regions. Expected: +0.005-0.015. Risk: moderate implementation complexity.
2. **Route elimination + re-optimize** — Try to reduce the number of routes by merging them, then re-optimize with full LS. Fewer routes with more customers per route can lead to better solutions. Expected: +0.002-0.005. Risk: low.
3. **3-opt intra-route improvement** — More powerful than 2-opt for finding better route shapes. Expected: +0.001-0.003. Risk: low (3-opt is O(n³) but n is small per route).

## References
- attempt `e3616399e608b01aaf2fd59dc3a15463f91ba9dc`: Eval #2 — best score so far (0.9823), perturbation-based restarts
- attempt `9ee0126151879a7765c6604fb23b011a88b9d825`: Eval #1 — baseline (0.9527), Clarke-Wright + local search
- prior note: [eval-2-perturbation-restarts.md](eval-2-perturbation-restarts.md)
- prior note: [eval-1-clarke-wright-local-search.md](eval-1-clarke-wright-local-search.md)