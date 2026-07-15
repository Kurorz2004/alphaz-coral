---
creator: captain-nemo
created: 2026-07-14T18:22:00+00:00
commit: e913a5a80385
type: experiment
claim: "Or-opt (segment relocation) + biased move selection gives marginal improvement from 0.9790 to 0.9794 — the trajectory is flattening and structural changes are needed"
status: confirmed
confidence: high
evidence:
  attempt: e913a5a80385
  score_delta: "+0.00035 (0.9790 → 0.9794)"
  verified: true
based_on: [ad9f2362387c]
touched: [solution.py]
tags: [cvrp, or-opt, segment-relocation, simulated-annealing]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T18:21:27.453661+00:00'
---

# Eval 5: Or-opt + biased move selection — score 0.9794, mean gap +2.12%

## Context

Fifth eval on the CVRP task. Added Or-opt moves (moving segments of 2-3 customers between routes) to the SA and the deterministic LS. Also changed move selection from uniform random to biased: 2-opt (35%), relocate (25%), exchange (15%), Or-opt (25%). Tested on 50 hidden instances.

## Result

| Metric | Eval 4 (SA+reheat) | This (Or-opt) | Δ |
|---|---|---|---|
| Score (mean ref/dist) | 0.9790 | 0.9794 | **+0.00035** |
| Mean gap | +2.17% | +2.12% | **-0.05pp** |
| Best gap | +0.14% (G100_1212_01) | +0.00% (G100_2334_01) | -0.14pp |
| Worst gap | +8.13% (G100_2266_01) | +5.94% (G100_3256_01) | -2.19pp |
| Total solve time | 475.3s | 475.4s | +0.1s |
| Dev instances score | 0.9827 | 0.9840 | **+0.0013** |

## Mechanism

- **Or-opt** moves segments of 2-3 consecutive customers between routes. This is more powerful than single-customer relocate because it preserves the internal ordering of the segment. The move type is particularly effective for instances where the route structure is good but customers are slightly misassigned.
- **Biased move selection** (35% 2-opt, 25% relocate, 15% exchange, 25% Or-opt) focuses the SA on the most effective move types. The acceptance rate of Or-opt is lower than relocate or 2-opt, but the moves that are accepted tend to be more valuable.
- The improvement is marginal (+0.00035), confirming that the SA is approaching its limit for this problem.

## What did not work

- **G100_2266_01 improved from +8.13% to +4.5%** — The Or-opt helped this instance significantly. But the overall impact is small because the improvement is concentrated in a few instances.
- **G100_3256_01 became the new worst instance at +5.94%** — This instance was previously at +1.5% in eval 4. The SA's stochastic nature means it sometimes finds worse solutions for some instances.
- **The trajectory is clearly flattening**: +0.1564 → +0.0296 → +0.0032 → +0.00035. Each improvement is 5-10x smaller than the previous.

## Next

1. **Cross-route 2-opt\*** — Estimated payoff: 0.979 → 0.982-0.987. A powerful inter-route move that swaps suffixes of two routes. This is a standard VRP neighborhood that the current SA doesn't explore. Risk: medium — needs careful delta computation and capacity checking.

2. **Multiple SA chains from different starting points** — Estimated payoff: 0.979 → 0.981-0.985. Run 3-4 shorter SA chains, each starting from a different randomized CW solution. This increases diversity and might find better solutions. Risk: low — simple change.

3. **Hyperparameter tuning** — Estimated payoff: 0.979 → 0.980-0.982. Tune SA parameters (alpha, T_initial, move probabilities) using a sweep. Risk: low — time-consuming but straightforward.

## References

- Baseline: [eval-4-sa-reheat.md](eval-4-sa-reheat.md) — SA with reheating, score 0.9790
- Baseline: [eval-3-sa.md](eval-3-sa.md) — SA without reheating, score 0.9758
- Baseline: [eval-2-cw-ls.md](eval-2-cw-ls.md) — CW + LS, score 0.9462
- Baseline: [eval-1-baseline-nn.md](eval-1-baseline-nn.md) — nearest-neighbor greedy, score 0.7898