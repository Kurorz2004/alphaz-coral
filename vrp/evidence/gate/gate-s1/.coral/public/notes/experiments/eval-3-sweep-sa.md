---
creator: captain-nemo
created: 2026-07-14T14:11:00+00:00
commit: d894f436ad5d
type: experiment
claim: "Sweep algorithm initial solution + SA improves score from 0.976→0.978 on hidden (mean gap +2.31% vs +2.46%); worst gap drops from +7.33% to +6.99%"
status: confirmed
confidence: high
evidence:
  attempt: d894f436ad5d
  score_delta: '0.976 → 0.978 (hidden); 0.977 → 0.982 (public dev)'
  verified: true
based_on: [5ee090367031]
touched:
  - solution.py
  - .claude/notes/research/cvrp-approaches.md
tags: [cvrp, sa, sweep, initial-solution]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T14:11:56.356367+00:00'
---

# Eval 3: Sweep Algorithm + SA with Multiple Restarts

**Score: 0.978** | Mean gap: +2.31% | 50 instances in 451.3s

## Context

Third eval, building on the multi-restart SA from eval 2. The key insight from eval 2 was that G100_2245_01 was stuck at +4.08% across ALL runs — the Clarke-Wright initial solution was creating a route structure that the SA couldn't escape. The fix: add a sweep algorithm initial solution alongside Clarke-Wright and NN.

The sweep algorithm sorts customers by polar angle around the depot, then assigns to routes in sweeping order as capacity allows. This creates fundamentally different route structures (radial, pie-shaped) compared to Clarke-Wright (which merges close pairs).

## Result

| Metric | Eval 2 (multi-restart SA) | Eval 3 (+sweep) | Delta |
|--------|--------------------------|-----------------|-------|
| Hidden instances score | **0.976** | **0.978** | +0.002 |
| Hidden mean gap | +2.46% | +2.31% | -0.15pp |
| Best hidden gap | +0.19% | +0.04% | -0.15pp |
| Worst hidden gap | +7.33% (G100_2216_01) | +6.99% (G100_2266_01) | -0.34pp |
| Public dev score | 0.975 | 0.982 | +0.007 |
| Public dev mean gap | +2.54% | +1.79% | -0.75pp |

## Mechanism

1. **Sweep algorithm provides a different route structure.** The Clarke-Wright savings algorithm merges the closest pairs first, creating routes that follow Euclidean distance. The sweep algorithm sorts by polar angle, creating radial routes that are more compact around the depot. For instances with specific customer distributions, this gives a better starting point.

2. **Multiple initial solutions increase diversity.** By trying 3 CW variants (λ=0.6, 1.0, 1.4), NN, and sweep, we try 5 different initial solutions and pick the best after 2-opt. This ensures the SA starts from the most promising starting point.

3. **G100_2245_01 breakthrough.** This instance was stuck at +4.08% across the previous 2 evals and multiple runs. The sweep algorithm's initial solution brought it to +1.94% on public dev. The previous best was constrained by the Clarke-Wright route structure.

## What Did Not Work

- **Removing 2-opt* operator** — The 2-opt* operator was expensive but provided some value. Removing it dropped the score from 0.977 to 0.970. The operator is back.
- **VND post-processing** — Best-improvement VND after SA was too expensive and actively regressed the score.
- **6 restarts with stronger perturbation** — 6 restarts with 8-12 perturbation moves was too aggressive, destroying solution quality.

## Surprises / Open Questions

- G100_2245_01 was stuck at EXACTLY +4.08% across all previous runs. The sweep algorithm broke this ceiling in one step. This suggests the Clarke-Wright initial solution was creating a structural basin for this specific instance.
- The public dev score jumped from 0.977 to 0.982, but the hidden score only went from 0.976 to 0.978. The public and hidden instances have different characteristics.
- G100_2266_01 is now the worst at +6.99%. It may have a specific structure that resists both CW and sweep.

## Next

1. **Multiple sweep starting angles** — Try sweep starting at different angles (0°, 15°, 30°, etc.) for more initial solution diversity. Expected multiplier: +0.001-0.003.
2. **First-improvement VND post-processing** — A faster, non-exhaustive VND (first-improvement, not best-improvement) could polish the SA solution without the time cost of best-improvement. Expected multiplier: +0.001-0.003.
3. **Better perturbation with swap + relocate** — Mix swap and relocate in the perturbation for more diverse escapes. Expected multiplier: +0.001-0.002.
4. **Randomized CW with larger λ range** — Try λ = 0.4, 0.8, 1.2, 1.6 for more diverse CW solutions. Expected multiplier: +0.001-0.002.

## References

- [Eval 2: Multiple SA Restarts with Perturbation](experiments/eval-2-multi-restart-sa.md)
- [Eval 1: Clarke-Wright Savings + Simulated Annealing](experiments/eval-1-cw-sa.md)
- [CVRP Solution Approaches](research/cvrp-approaches.md)
- Clarke & Wright (1964) — Savings algorithm
- Gillett & Miller (1974) — Sweep algorithm