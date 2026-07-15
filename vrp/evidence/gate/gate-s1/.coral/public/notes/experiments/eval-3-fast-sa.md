---
creator: captain-ahab
created: 2026-07-14T13:48:52+00:00
commit: 10039a6829d1
type: experiment
claim: "Fast SA with adaptive operator weights (ALNS-style) achieves 0.960 on hidden instances — worse than VND-based approach"
status: confirmed
confidence: high
evidence:
  attempt: 10039a6829d1
  score_delta: 0.971 → 0.960 (hidden); 0.962 → 0.958 (public dev)
  verified: true
based_on: [22a3059c1339]
touched: [solution.py]
tags: [cvrp, sa, alns, adaptive-weights]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T13:50:22.907459+00:00'
---

# Eval 3: Fast SA with Adaptive Operator Weights (ALNS-style)

**Score: 0.960** | Mean gap: +4.26% | 50 instances in 465.1s

## Context

After eval-2 (VND + ILS at 0.971), the Next section suggested trying a faster SA inner loop. The hypothesis was that many more SA iterations (1000+) with random single-operator moves would explore more broadly than the VND (10-18 iterations). This eval tests that hypothesis.

## Result

| Metric | Eval 2 (VND+ILS) | This attempt (SA) | Δ |
|--------|-----------------|-------------------|---|
| Hidden instances score | 0.971 | **0.960** | −0.011 |
| Hidden instances mean gap | +3.01% | +4.26% | +1.25pp |
| Best hidden gap | +0.17% (G100_3226_01) | +0.45% (G100_1211_01) | +0.28pp |
| Worst hidden gap | +8.65% (G100_3344_01) | +10.56% (G100_1155_01) | +1.91pp |
| Total time (50 instances) | 450.4s | 465.1s | +14.7s |

## Mechanism

1. **SA with random single-operator moves** does not converge as well as best-improvement VND. Each SA iteration tries one random move (relocate, exchange, 2-opt*, or 2-opt) and accepts it with SA probability. This is fundamentally a weaker local search than VND's best-improvement over all moves.

2. **Adaptive weights (ALNS-style)** select operators based on success rate. This helps but doesn't close the gap — the fundamental issue is that random single moves don't find the best improvement quickly enough.

3. **The SA version runs ~2000-5000 iterations per instance** vs VND's ~10-18 ILS iterations. Despite 100-500x more iterations, the per-iteration quality is so much lower that the overall solution quality is worse.

4. **Surprising counterexample**: SA is better on some instances (G100_2134_01: +2.77% vs +10.59% for VND). This suggests that on instances where the VND gets stuck in a poor local optimum, SA's broader exploration helps.

## What Did Not Work

- **Random single-operator moves** — The core hypothesis was wrong. 1000+ random moves don't compensate for the lack of systematic search. Best-improvement in each neighborhood is critical.
- **Adaptive weights** — The operator selection didn't significantly improve over equal weights. The success rates were similar across operators.
- **SA acceptance of worsening moves** — Accepting too many worsening moves diluted the search, spending time on poor solutions.

## Surprises / Open Questions

- The hypothesis was wrong: more iterations × weaker search ≠ better solutions. VND's best-improvement search is much more effective per unit time.
- Some instances improved with SA (G100_2134_01 went from +10.59% to +2.77%). This suggests a hybrid approach could work: VND as the main search, with periodic SA-style perturbation to escape deep local optima.
- The current VND version already does this (ILS perturbation + VND re-optimization). The difference is that the ILS perturbation is random, while SA would be more targeted.

## Next

1. **Granular neighborhoods for VND** — Speed up the VND by limiting inter-route moves to the nearest ~40 customers. This would allow more ILS iterations in the same time budget. Expected payoff: +0.003-0.008.
2. **Stronger perturbation** — Move 4-6 customers instead of 2-3 for better diversification. Expected payoff: +0.002-0.005.
3. **Add Or-opt operator** — Move sequences of 2-3 consecutive customers. Expected payoff: +0.002-0.003.
4. **Multiple restarts** — Run 3-4 shorter ILS chains from different starting points. Expected payoff: +0.001-0.003.

## References

- [Eval 2: Clarke-Wright + VND + ILS](eval-2-cw-vnd-ils.md) — the best attempt at 0.971
- [Eval 1: Clarke-Wright Savings + Simulated Annealing](eval-1-cw-sa.md) — captain-nemo's baseline
- attempt `22a3059c`: VND+ILS at 0.971 (best so far)
- attempt `69923112`: captain-nemo's SA at 0.962