---
creator: captain-ahab
created: 2026-07-14T09:30:00Z
commit: 621880b994a1
type: experiment
claim: "ILS perturbation of best solution + re-optimize between CW restarts raises score from 0.975 to 0.987"
status: confirmed
confidence: high
evidence:
  attempt: 621880b994a1
  score_delta: "+0.0117"
  verified: true
based_on: [experiments/eval-1-clarke-wright-local-search.md]
touched: [solution.py]
tags: [ils, perturbation, cw, 2opt, relocate, exchange, cross]
---

# ILS perturbation + CW multi-restart: 0.975 → 0.987

## Context

Eval #1 (score 0.975) used independent CW+LS restarts filling the full time budget. The insight was that starting from scratch each time wastes the structure already found in good solutions. Eval #2 adds Iterated Local Search (ILS): after ~30 CW restarts, the solver repeatedly perturbs the best solution and re-optimizes, accepting only improvements.

## Result

**Score: 0.986937** (+0.0117 over eval #1, +0.2327 over baseline)

| Instance group | Eval #1 gap | Eval #2 gap | Change |
|---------------|-------------|-------------|--------|
| Best instance | +0.27%      | -0.10%      | beat reference! |
| Mean          | +2.56%      | +1.33%      | -1.23pp |
| Worst 5       | +4.0%–5.8%  | +2.6%–3.9%  | -2pp typical |

12 of 50 instances now within 0.5% of reference. 4 instances under 0.1%.

## Mechanism

1. **Phase 1 (CW multi-restart)** — Same as before: 30 CW+LS cycles with varying noise to explore diverse basins. Each cycle ~32ms.

2. **Phase 2 (ILS)** — Take the best solution from Phase 1, gently perturb it (remove 5-17% of customers and re-insert at cheapest feasible position), then re-run full LS. Each cycle ~8-15ms (faster than CW+LS because starting from near-optimal).

3. **Why it works** — Independent CW restarts explore different *uncorrelated* basins. ILS explores the *neighborhood* of the best basin. The combination (exploration + exploitation) is more efficient than either alone.

4. **Improvement-only acceptance** — The initial ILS version tried Record-to-Record Travel (accepting solutions within 2% of best). This regressed some instances (G100_3133: +4.57% → +7.25%) because accepting bad solutions allowed drift away from good structure. Switching to improvement-only acceptance fixed this.

## What did not work

- **Record-to-Record Travel** — Accepting solutions within a threshold of the best caused catastrophic drift on tight-capacity instances (capacity ≤ 100). The perturbation often creates more routes than needed, and LS cannot always undo this. Threshold-based acceptance compounds the problem. Restored to improvement-only.

- **Over-perturbation** — The first ILS version used intensity up to 28%. This was too strong for small-capacity instances where any route change risks infeasibility. Reduced to 5-17%.

## Surprises / open questions

- **Beat the reference on 1 instance** — G100_3374_01 at -0.10%. This confirms the reference is slightly loose (it's a strong heuristic, not an optimum). This instance had capacity 161 and moderate difficulty.
- **Worst instances share no obvious pattern** — G100_3173 (+3.74%) has capacity 157; G100_3174 (+3.93%) has capacity 206; G100_1155 (+3.49%) has capacity 1137. No single structural feature (tight capacity, clustered customers, etc.) explains all worst performers.
- **Time is still the budget constraint** — 476s total, ~9.5s/instance. With ~600 ILS cycles and 30 CW cycles, the solver is running to the deadline on every instance.
- **Further gains diminishing** — Eval #1: +0.221 from baseline. Eval #2: +0.012 from eval #1. Expect next improvements to be smaller.

## Next

In descending order of expected payoff:

1. **Or-opt (intra-route segment relocate)** — Move 2-3 consecutive customers within a route to a different position. 2-opt reverses segments but cannot *move* them — a well-known gap in 2-opt coverage. Expected: +0.002 to +0.005. Risk: low.

2. **Inter-route Or-opt** — Move segments of 2-3 customers between routes. Relocate handles single customers; segment relocation can discover qualitatively different route structures. Expected: +0.002 to +0.004. Risk: low.

3. **Sweep construction heuristic** — As an alternative to CW, provides a completely different set of initial solutions. Combine with CW in Phase 1 for better diversity. Expected: +0.001 to +0.003. Risk: low.

4. **Simulated Annealing in ILS phase** — Accept worsening solutions with probability exp(-delta/T). Could help escape deep local minima. Requires temperature tuning. Expected: +0.001 to +0.003. Risk: medium (tuning).

## References

- [experiments/eval-1-clarke-wright-local-search.md](experiments/eval-1-clarke-wright-local-search.md)
- Or-opt: I. Or, "Traveling Salesman-Type Combinatorial Problems" (1976)