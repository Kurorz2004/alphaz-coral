---
creator: captain-ahab
created: 2026-07-14T14:01:35+00:00
commit: e61b9dea83df
type: experiment
claim: "Granular neighborhoods (theta=40) + Or-opt operator + stronger perturbation (3-5 customers) achieves 0.975 on hidden instances"
status: confirmed
confidence: high
evidence:
  attempt: e61b9dea83df
  score_delta: 0.971 → 0.975 (hidden); 0.962 → 0.972 (public dev)
  verified: true
based_on: [22a3059c1339, 10039a6829d1]
touched: [solution.py]
tags: [cvrp, vnd, ils, granular, or-opt]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T14:02:11.269673+00:00'
---

# Eval 4: Granular Neighborhoods + Or-opt + Stronger Perturbation

**Score: 0.975** | Mean gap: +2.63% | 50 instances in 450.3s

## Context

After eval-2 (VND + ILS at 0.971) and eval-3 (SA at 0.960 — regressed), returning to the VND approach with three improvements:
- **Granular neighborhoods** (theta=40) — restrict inter-route moves to the nearest 40 customers, drastically reducing the VND search space
- **Or-opt operator** — move sequences of 2-3 consecutive customers to another route
- **Stronger perturbation** — relocate 3-5 customers instead of 2-3 in the ILS loop

## Result

| Metric | Eval 2 (VND+ILS) | This attempt | Δ |
|--------|-----------------|-------------|---|
| Hidden instances score | 0.971 | **0.975** | +0.004 |
| Hidden instances mean gap | +3.01% | +2.63% | −0.38pp |
| Best hidden gap | +0.17% (G100_3226_01) | +0.10% (G100_1211_01) | −0.07pp |
| Worst hidden gap | +8.65% (G100_3344_01) | +8.14% (G100_3374_01) | −0.51pp |
| Total time (50 instances) | 450.4s | 450.3s | — |

## Mechanism

1. **Granular neighborhoods (theta=40)** — The most impactful change. By restricting inter-route moves to the nearest 40 customers, the VND runs faster and finds more ILS iterations in the same time budget. The speedup is especially significant for the relocate operator, which previously checked all possible (route, position) pairs.

2. **Or-opt operator** — Moving sequences of 2-3 consecutive customers is more effective than moving individual customers. It preserves the local ordering within the sequence, which is valuable for maintaining good route structure.

3. **Stronger perturbation (3-5 customers)** — Moving more customers in the perturbation step helps the ILS escape deep local optima. The previous perturbation (2-3 customers) was too weak to escape the basin of attraction.

4. **The combination is synergistic**: granular neighborhoods make the VND faster, which allows more ILS iterations, and the stronger perturbation actually helps rather than hurting because there are more iterations to recover.

## What Did Not Work

- **SA approach (eval-3)** — Already confirmed: random single-operator moves don't match VND's best-improvement search. The per-iteration quality gap is too large.
- **Theta too small (20)** — In earlier testing, theta=20 missed too many good moves. Theta=40 is a good balance.
- **Or-opt without granular** — The Or-opt operator is expensive without granular restrictions. With granular, it's efficient.

## Surprises / Open Questions

- The worst-case changed from G100_3344_01 (+8.65% → +6.21%) to G100_3374_01 (+8.14%). The gap distribution shifted but the long tail persists.
- The best instance is now within 0.1% of the reference — essentially optimal.
- The granular restriction (theta=40) might be too aggressive for some instances. Theta=50 could be a better default, or adaptive theta based on instance size.
- Multiple restarts could help the worst-case instances more than a single long ILS chain.

## Next

1. **Multiple restarts** — Run 3-4 shorter ILS chains from different starting points (different perturbations of the initial solution). Each chain gets 2-3 seconds instead of 9. This could help escape deep local optima. Expected payoff: +0.003-0.005.
2. **Tune granular neighborhood size** — Try theta=30 for tight-capacity instances and theta=50 for loose-capacity. Expected payoff: +0.001-0.003.
3. **Add SWAP* operator** — Optimal inter-route swap from Vidal (2020). Complex but could help the worst-case instances. Expected payoff: +0.001-0.003.
4. **Guided perturbation** — Instead of random relocation, perturb by moving customers from the longest routes to the shortest. Expected payoff: +0.001-0.002.

## References

- [Eval 2: Clarke-Wright + VND + ILS](eval-2-cw-vnd-ils.md) — baseline at 0.971
- [Eval 3: Fast SA with Adaptive Weights](eval-3-fast-sa.md) — SA regression at 0.960
- [CVRP Solution Approaches](../research/cvrp-approaches.md) — literature survey
- attempt `22a3059c`: VND+ILS at 0.971
- attempt `10039a68`: SA at 0.960
- Vidal (2012, 2020) — HGS with 2-opt* and SWAP* neighborhoods, granular search concept