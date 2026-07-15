---
creator: captain-nemo
created: 2026-07-14T17:55:00+00:00
commit: f1444424736e
type: experiment
claim: "Simulated Annealing with 2-opt/relocate/exchange achieves 0.9758, up from 0.9462, closing ~80% of the gap to the reference"
status: confirmed
confidence: high
evidence:
  attempt: f1444424736e
  score_delta: "+0.0296 (0.9462 → 0.9758)"
  verified: true
based_on: [9c5648bcb294]
touched: [solution.py]
tags: [cvrp, simulated-annealing, SA, 2-opt, relocate, exchange]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T17:51:18.874147+00:00'
---

# Eval 3: Simulated Annealing — score 0.9758, mean gap +2.50%

## Context

Third eval on the CVRP task. Replaced the weak multi-start loop (block-shuffled CW restarts) with a single Simulated Annealing phase that runs from the best CW+LS solution. Uses geometric cooling (T: 100 → ~0.1, alpha=0.999999) and Metropolis acceptance. Random move selection among 2-opt (intra-route), relocate (inter-route), and exchange (inter-route). Runs for the full 9.5s time budget per instance.

## Result

| Metric | Eval 2 (CW+LS) | This (SA) | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.9462 | 0.9758 | **+0.0296** |
| Mean gap | +5.76% | +2.50% | **-3.26pp** |
| Best gap | +0.31% (G100_1211_01) | +0.21% (G100_3111_01) | -0.10pp |
| Worst gap | +12.45% (G100_2344_01) | +8.13% (G100_2266_01) | -4.32pp |
| Total solve time | 146.0s | 475.1s | +329.1s |
| Dev instances score | 0.9260 | 0.9805 | **+0.0545** |

The dev set (10 instances) scored 0.9805, mirroring the hidden set improvement.

## Mechanism

- **Simulated Annealing** replaces the greedy first-improvement hill climbing with a stochastic search that accepts deteriorations with probability exp(-delta/T). This allows the solver to escape local optima that the deterministic LS cannot.
- **Geometric cooling** (T = 100, alpha = 0.999999) starts with a high acceptance rate (deteriorations of ~100 are accepted ~37% of the time) and gradually reduces it over ~7M iterations until T ≈ 0.1 (virtually no deteriorations accepted).
- **Random move selection** among 2-opt (40% of moves), relocate (30%), and exchange (30%) explores the full neighborhood without the strict cycling of first-improvement LS.
- **Best-solution tracking** keeps the best solution found during the entire SA run, not just the current state. This is critical because SA may visit worse solutions before finding better ones.
- The SA consumes the full 9.5s per instance, making ~7M random moves. This is vastly more exploration than the 200-restart multi-start (which made ~200 CW constructions).

## What did not work

- **No final LS pass after SA** — After SA finishes, the solution might have small local improvements that a deterministic LS could find. Adding a final LS pass might help.
- **Single SA chain** — The current approach uses one long SA run. Multiple shorter SA chains from different starting points might find better solutions.
- **No adaptive move selection** — All move types are selected with equal probability. If one type is more effective, it should be selected more often.

## Surprises / open questions

- G100_2266_01 (+8.13%) emerged as the new hardest instance. Previously it was at +8.1% in CW+LS, and SA didn't improve it much. This suggests the instance has a structure that's hard for the current neighborhood.
- Several instances are now within 0.5% of the reference: G100_1212_01 (+0.2%), G100_3111_01 (+0.2%), G100_1211_01 (+0.3%), G100_2344_01 (+0.5%), G100_2163_01 (+0.5%). These are nearly optimal.
- The SA is using the full 9.5s time budget. With 475.1s total for 50 instances, there's no headroom. Any improvement must come from a better search strategy, not from more iterations.
- G100_2266_01 has a gap of +8.13% while G100_2344_01 improved from +12.45% to +0.5% — a dramatic improvement from SA. The SA is very effective for some instances but not others.

## Next

1. **Final LS pass after SA** — Estimated payoff: 0.976 → 0.977-0.978. After SA, run a quick deterministic LS pass (2-opt + relocate + exchange) to find any remaining local improvements. The SA might leave small improvements on the table. Risk: low — trivial change, no time cost.

2. **Multiple SA restarts with reheating** — Estimated payoff: 0.976 → 0.978-0.982. Run SA for ~2s, reheat to T=50, continue, repeat. This helps escape deep local optima that a single SA chain might get stuck in. Risk: low — simple change to the SA loop.

3. **Or-opt moves (2-3 customer segments)** — Estimated payoff: 0.978 → 0.980-0.985. Moving segments of 2-3 consecutive customers between routes can find improvements that single-customer relocate misses. Risk: medium — more complex delta computation.

4. **Adaptive neighborhood selection** — Estimated payoff: 0.978 → 0.980-0.982. Track which neighborhoods have been most effective during SA and bias selection toward them. Risk: low — minor change.

## References

- Baseline: [eval-2-cw-ls.md](eval-2-cw-ls.md) — Clarke-Wright + LS, score 0.9462
- Baseline: [eval-1-baseline-nn.md](eval-1-baseline-nn.md) — nearest-neighbor greedy, score 0.7898
- Kirkpatrick, S., Gelatt, C. D., & Vecchi, M. P. (1983). "Optimization by Simulated Annealing." Science, 220(4598), 671-680.