---
creator: captain-nemo
created: 2026-07-14T18:05:00+00:00
commit: ad9f2362387c
type: experiment
claim: "SA reheating + final LS polish improves score from 0.9758 to 0.9790, but the trajectory is flattening — need structural changes for further gains"
status: confirmed
confidence: high
evidence:
  attempt: ad9f2362387c
  score_delta: "+0.0032 (0.9758 → 0.9790)"
  verified: true
based_on: [f1444424736e]
touched: [solution.py]
tags: [cvrp, simulated-annealing, reheating, local-search]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T18:03:54.323960+00:00'
---

# Eval 4: SA reheating + final LS — score 0.9790, mean gap +2.17%

## Context

Fourth eval on the CVRP task. Added SA reheating (when T < 0.1, reheat to 50) and a final deterministic LS pass after SA finishes. The goal was to escape deeper local optima that the single cooling chain of the prior SA could not.

## Result

| Metric | Eval 3 (SA) | This (SA+reheat+LS) | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.9758 | 0.9790 | **+0.0032** |
| Mean gap | +2.50% | +2.17% | **-0.33pp** |
| Best gap | +0.21% (G100_3111_01) | +0.14% (G100_1212_01) | -0.07pp |
| Worst gap | +8.13% (G100_2266_01) | +8.13% (G100_2266_01) | 0.00pp |
| Total solve time | 475.1s | 475.3s | +0.2s |
| Dev instances score | 0.9805 | 0.9827 | **+0.0022** |

## Mechanism

- **Reheating** — When T drops below 0.1, the temperature is reset to 50 and the SA continues. This gives the search a second chance to escape local optima. The effect is modest (+0.0032) because the SA already explores the neighborhood well.
- **Final LS polish** — A deterministic 2-opt + relocate + exchange pass after SA. This finds any remaining local improvements that the SA's stochastic search might have missed. The effect is small because the SA's low-temperature phase already acts as a local search.
- The trajectory is clearly flattening: +0.1564 → +0.0296 → +0.0032. Each improvement is ~5x smaller than the previous.

## What did not work

- **G100_2266_01 is still at +8.13%** — This instance is completely resistant to the current neighborhoods. The SA cannot find a better solution for it regardless of the reheating or final LS.
- **Reheating alone is not enough** — The reheating mechanism helps for some instances but the overall effect is small. The SA is already converging to the best solution in the neighborhood, and reheating doesn't help escape truly deep local optima.

## Surprises / open questions

- G100_2266_01 is the only instance that hasn't improved across multiple evals. It seems to be structurally different from the others. The CW + SA approach might be stuck in a local optimum that none of the current move types can escape.
- The dev set score (0.9827) is now higher than the hidden set (0.9790), suggesting the dev set is slightly easier for this algorithm.
- Several instances are now within 1% of the reference. The remaining gap is concentrated in a few hard instances.

## Next

1. **Or-opt moves (segment relocation)** — Estimated payoff: 0.979 → 0.982-0.987. Moving segments of 2-3 consecutive customers between routes can find improvements that single-customer relocate misses. This is the most promising structural addition. Risk: medium — more complex delta computation.

2. **Multiple SA chains from different starting points** — Estimated payoff: 0.979 → 0.981-0.985. Run 3-4 shorter SA chains, each starting from a different randomized CW solution. This increases diversity and might find better solutions. Risk: low — simple change.

3. **Hyperparameter tuning** — Estimated payoff: 0.979 → 0.980-0.982. Tune SA parameters (alpha, T_initial, move probabilities) using a sweep. Risk: low — time-consuming but straightforward.

## References

- Baseline: [eval-3-sa.md](eval-3-sa.md) — SA without reheating, score 0.9758
- Baseline: [eval-2-cw-ls.md](eval-2-cw-ls.md) — CW + LS, score 0.9462
- Baseline: [eval-1-baseline-nn.md](eval-1-baseline-nn.md) — nearest-neighbor greedy, score 0.7898