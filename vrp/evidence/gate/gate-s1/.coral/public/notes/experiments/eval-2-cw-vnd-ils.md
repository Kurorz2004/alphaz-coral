---
creator: captain-ahab
created: 2026-07-14T13:30:56+00:00
commit: 22a3059c1339
type: experiment
claim: "Clarke-Wright savings + VND (relocate, exchange, 2-opt*) + ILS with SA acceptance achieves 0.971 on hidden instances"
status: confirmed
confidence: high
evidence:
  attempt: 22a3059c1339
  score_delta: 0.962 → 0.971 (hidden); 0.754 → 0.962 (public dev)
  verified: true
based_on: [6992311215e7]
touched: [solution.py]
tags: [cvrp, vnd, ils, clarke-wright, sa]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T13:31:52.614499+00:00'
---

# Eval 2: Clarke-Wright + VND + ILS

**Score: 0.971** | Mean gap: +3.01% | 50 instances in 450.4s

## Context

Building on eval-1 (captain-nemo, scored 0.962, SA with relocate/swap/2-opt). Key differences:
- **Added 2-opt* (cross-route exchange)** operator — the most impactful single operator per CVRP literature
- **Replaced inline SA with VND (Variable Neighborhood Descent)** — best-improvement search over relocate, exchange, 2-opt*
- **Added ILS (Iterated Local Search) outer loop** — perturb the current solution, then re-optimize via VND
- **SA acceptance criterion** for the ILS outer loop — accept worsening solutions with probability exp(-Δ/T)
- **Best-improvement** (not first-improvement) for all operators

## Result

| Metric | Eval 1 (captain-nemo) | This attempt | Δ |
|--------|----------------------|-------------|---|
| Hidden instances score | 0.962 | **0.971** | +0.009 |
| Hidden instances mean gap | +3.96% | +3.01% | −0.95pp |
| Best hidden gap | +0.19% (G100_1212_01) | +0.17% (G100_3226_01) | −0.02pp |
| Worst hidden gap | +9.04% (G100_3344_01) | +8.65% (G100_3344_01) | −0.39pp |
| Total time (50 instances) | 451.3s | 450.4s | — |

## Mechanism

1. **2-opt*** (cross-route exchange) is the most impactful single addition. It exchanges the tail segments of two routes, which can fundamentally restructure the solution. The previous SA implementation only had relocate, swap, and intra-route 2-opt.

2. **Best-improvement search** (instead of first-improvement / random sampling) finds the best possible move in each neighborhood, leading to higher-quality local optima.

3. **VND + ILS**: The VND intensifies to a local optimum, then the ILS perturbation + SA acceptance provides diversification. More structured than random-SA.

4. **Best-improvement 2-opt** (full sweep until no improvement) is more thorough than per-iteration random 2-opt. Particularly helps on loose-capacity instances.

## What Did Not Work

- **Multiple initial solutions** — Trying both savings and greedy with different seeds didn't significantly improve over just savings.
- **Fast local search** (single round of each operator per ILS iteration) — Converged too quickly to poor local optima. Full VND per iteration is slower but better.
- **Greedy nearest-neighbor randomization** — Partially-randomized nearest-neighbor produced worse initial solutions than pure savings.

## Surprises / Open Questions

- The worst-case instance is still G100_3344_01 at +8.65% gap (tight capacity, ~10 routes). The solver struggles to find the right structure.
- Best instances are within 0.2% of the reference — nearly optimal.
- VND is expensive: each ILS iteration takes ~0.5-1s, limiting total iterations to ~10-18 per 9s budget. A faster inner loop could help the tail.

## Next

1. **Faster SA inner loop** — Replace VND with pure SA (1000+ iterations vs 10-18). Each iteration picks a random operator and evaluates one move. More exploration at the cost of per-iteration quality. Expected payoff: +0.005-0.01.
2. **Adaptive operator weights (ALNS-style)** — Track which operators improve most and select them more frequently. Expected payoff: +0.003-0.005.
3. **Stronger perturbation** — Move 3-5 customers instead of 2-3 for better diversification. Expected payoff: +0.002-0.005.
4. **Or-opt operator** — Move sequences of 2-3 consecutive customers. Expected payoff: +0.002-0.003.

## References

- [Eval 1: Clarke-Wright Savings + Simulated Annealing](eval-1-cw-sa.md) — captain-nemo's baseline at 0.962
- [CVRP Solution Approaches](../research/cvrp-approaches.md) — literature survey
- attempt `6992311215e7`: captain-nemo's SA baseline
- Vidal (2012, 2020) — HGS with 2-opt* and SWAP* neighborhoods