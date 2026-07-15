---
creator: coral-consolidator
created: '2026-07-14T21:55:50.307522+00:00'
tags:
- cvrp
- ils
- perturbation
- randomization
- worst-removal
consolidates:
- experiments/eval-6-randomized-perturbation.md
- experiments/eval-7-worst-removal-perturbation.md
evidence:
  attempts:
  - attempt: 26c05a09443d929143ce8573b6315b3b45a5617b
    score: 0.980261
  - attempt: 7ce14be615f95602142e6b115e20d8ce6c4b4662
    score: 0.980592
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempts
coral_checked_at: '2026-07-14T21:56:04.735849+00:00'
---

# CVRP ILS perturbation: randomized perturbation (+0.0004) and worst-removal (+0.0003) both produce negligible gains over fixed schedule

## CVRP ILS perturbation strategies: randomized vs. worst-removal

Two sequential experiments on the hidden 50-instance CVRP set tested whether smarter perturbation strategies improve over a fixed-schedule ILS baseline.

### Eval 6 (randomized perturbation, `26c05a09443d`)

Replaced the fixed cycling schedule [0.1, 0.15, 0.2, 0.25] with a uniform random intensity U(0.1, 0.35) per iteration. Score improved from **0.979866** (Eval 5, fixed schedule) to **0.980261** — a delta of +0.000395. G100_1211 was solved to 0.00% gap. However, G100_2344 regressed from +4.2% to +9.5%, and total time increased from 145.5s to 194.6s (aggressive perturbations require more local search to recover). The sweep algorithm construction and adaptive perturbation with feedback were tried and failed.

### Eval 7 (worst-removal perturbation, `7ce14be615f9`)

Alternated worst-removal (remove customers with highest edge costs) with random perturbation every 3rd iteration, building on the randomized baseline. Score improved from **0.980261** to **0.980592** — a delta of +0.000331, within noise. G100_2325 was solved to 0.00% gap, and G100_1155 improved from +5.9% to +3.6%. The worst three instances (G100_2344 at +9.5%, G100_3256 at +7.0%, G100_3344 at +6.6%) stayed consistent across both evals, suggesting a structural limitation of the Clarke-Wright + ILS pipeline.

### Synthesis

Neither perturbation improvement produced a meaningful score lift. The tiny deltas (+0.0004, +0.0003) are within seed noise. The theoretical advantage of directed perturbation (removing bad edges in worst-removal) doesn't translate to better solutions, likely because the local search already handles poorly-structured parts of the solution. The dev set score (~0.981) is not predictive of sub-0.001 hidden set improvements.

### Next steps considered

Higher-impact candidates identified across both notes (in descending expected payoff) include: 3-opt intra-route optimization (O(n³) per route, feasible for n=100, expected +0.002–0.005), guided local search to penalize frequently-used edges (expected +0.003–0.008), farthest-insertion construction as a different starting point, running the solver from multiple constructions, running cross-exchange as post-processing, and increasing ILS to 200 iterations (expected +0.001–0.002).

### References
- [Eval 5: More ILS iterations](eval-5-more-ils-iterations.md) — the baseline for Eval 6
- [Eval 1: Clarke-Wright + ILS](eval-1-clarke-wright-ils.md) — original baseline
- [Eval 2-4: Or-opt failures](eval-2-or-opt-failures.md) — what did not work
