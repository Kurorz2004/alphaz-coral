---
creator: captain-nemo
created: 2026-07-15T05:30:00
commit: 0e907eecd1d33c3c9f10b44a683337fd05bb9851
type: experiment
claim: "Increasing ILS to 200 iterations with expanded noise levels improves score from 0.9806 to 0.9814 on the hidden 50-instance CVRP set"
status: confirmed
confidence: high
evidence:
  attempt: 0e907eecd1d3
  score_delta: 0.000796
  verified: true
based_on: [26c05a09443d]
touched: [solution.py]
tags: [cvrp, ils, iteration-budget, noise]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T22:12:50.811837+00:00'
---

# Eval 8: More ILS iterations (200) + expanded noise — score 0.9814

## Context

After establishing that 150 ILS iterations with randomized perturbation
produces a score of 0.9806 (Eval 7), the next step was to increase the
iteration budget to 200 and expand the noise levels for Clarke-Wright
restarts (adding 12.0 and 16.0 to the noise schedule).

## Result

| Metric | Eval 7 (150 iters) | Eval 8 (200 iters) | Delta |
|--------|-------------------|--------------------|-------|
| **Score** | **0.980592** | **0.981388** | **+0.000796** |
| Mean gap | +2.01% | +1.93% | -0.08% |
| Best gap | +0.01% (G100_2111) | +0.00% (G100_1211) | -0.01% |
| Worst gap | +9.51% (G100_2344) | +9.51% (G100_2344) | 0.00% |
| Solved | 50 in 189.6s | 50 in 230.3s | +40.7s |

## Mechanism

More ILS iterations (200 vs 150) allow the solver to explore more candidate
solutions. The expanded noise levels (adding 12.0 and 16.0) create more
diverse starting points for the Clarke-Wright restarts, which helps escape
local optima on some instances.

Most instances improved slightly (e.g., G100_1112 from +3.0% to +1.1%,
G100_1375 from +3.2% to +1.3%). The worst-gap instances (G100_2344, G100_3256,
G100_1155) remain unchanged.

## What did not work

- **Guided Local Search (GLS)** — Added penalty-based diversification to the
  local search. The GLS penalties didn't find better solutions than the random
  perturbation, and the extra local search per iteration doubled the runtime.
- **3-opt intra-route** — Too expensive. All instances hit the 9s deadline.
  O(n³) per route is feasible for n=100 but the 3-opt runs multiple iterations.
- **Sweep algorithm construction** — Sweep (polar angle sort) was much worse
  than Clarke-Wright on all instances.
- **Farthest-insertion construction** — Also much worse than Clarke-Wright.
- **Worst-removal perturbation** — No meaningful improvement over random.

## Surprises / open questions

- G100_2344_01 remains the worst at +9.51% across multiple evals. This
  instance has a specific topology (clustered customers) that the
  Clarke-Wright + ILS pipeline cannot handle well.
- G100_1211_01 is now solved to 0.00% gap — the reference distance is
  matched exactly.
- The total time (230.3s for 50 instances) is well within the 500s budget.
  Average per-instance time is ~4.6s.
- The dev set score (0.982) consistently overestimates the hidden set score
  by ~0.0006 (0.982 vs 0.9814).

## Next

In descending expected payoff:

1. **More frequent noisy restarts** — Change the restart frequency from every
   5th iteration to every 3rd iteration. This increases diversity and might
   help the stubborn instances. Expected: +0.001-0.003.

2. **Tabu search** — Keep a tabu list of recently perturbed solutions to
   prevent revisiting. More complex than current approach. Expected:
   +0.002-0.005.

3. **Variable Neighborhood Search (VNS)** — Systematically change the
   perturbation intensity (small, medium, large) in a structured way.
   Expected: +0.001-0.003.

4. **Accept current candidate as next perturbation base** — Instead of always
   perturbing the best solution, sometimes perturb the current candidate
   even if it's worse. This is like ILS with random walk. Expected:
   +0.001-0.002.

## References

- [Eval 7: Worst-removal perturbation](eval-7-worst-removal-perturbation.md)
- [Eval 6: Randomized perturbation](eval-6-randomized-perturbation.md)
- [Eval 5: More ILS iterations](eval-5-more-ils-iterations.md)
- [Eval 1: Clarke-Wright + ILS](eval-1-clarke-wright-ils.md)