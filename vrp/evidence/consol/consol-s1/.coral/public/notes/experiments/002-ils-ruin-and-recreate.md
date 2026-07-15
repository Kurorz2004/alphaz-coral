---
creator: captain-ahab
created: 2026-07-15T01:00:00
type: experiment
name: 002-ils-ruin-and-recreate
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T18:41:10.571482+00:00'
---

# Experiment 002: ILS with Ruin-and-Recreate

## Hypothesis

After VND converges to a local optimum, the only way to find a better solution is to escape the current basin of attraction. Ruin-and-recreate (remove customers, reinsert with cheapest insertion) provides a strong perturbation that moves the solution to a different part of the search space, after which VND finds a new local optimum — potentially better than the previous one.

## Design

- **Phase 1:** Clarke-Wright deterministic construction + VND (10 passes)
- **Phase 2:** ILS cycle: ruin-and-recreate (remove 10-30% random customers) + cheapest insertion repair + VND (10 passes)
- 5 ruin fractions × 5 iterations = 25 ILS cycles
- Accept only if strictly better

### Key parameters
- Ruin fractions: 0.10, 0.15, 0.20, 0.25, 0.30
- VND: 2-opt, Or-opt, Relocate, Exchange, 2-opt* (10 passes max)
- Insertion: cheapest insertion (try all routes, all positions)

## Results

| Metric | Eval #1 (VND+multi-start) | Eval #2 (ILS+ruin) |
|--------|--------------------------|-------------------|
| Score | 0.9566 | 0.9643 |
| Mean gap | +4.59% | +3.75% |
| Best gap | +0.19% | +0.20% |
| Worst gap | +9.36% | +9.01% |
| Time | 477.8s (50 instances) | 25.8s (50 instances) |

Improvement: **+0.77%** in score, **-0.84pp** mean gap, **18x faster**.

### Per-instance comparison (public dev set)
| Instance | VND-only | ILS+ruin | Improvement |
|----------|----------|----------|-------------|
| G100_1165_01 | 11318 | 10924 | -394 |
| G100_1265_01 | 7055 | 7055 | 0 |
| G100_1312_01 | 23442 | 23473 | +31 |
| G100_1356_01 | 9468 | 9468 | 0 |
| G100_2134_01 | 12287 | 11992 | -295 |
| G100_2245_01 | 7081 | 7090 | +9 |
| G100_2325_01 | 9787 | 9686 | -101 |
| G100_2371_01 | 29604 | 28967 | -637 |
| G100_3133_01 | 20313 | 20319 | +6 |
| G100_3166_01 | 10429 | 9713 | -716 |

## Analysis

### What worked
- **Ruin-and-recreate** is a very effective perturbation strategy — it moves the solution to a different basin reliably
- **Cheapest insertion** repair produces high-quality solutions that are often better than the original
- The combination of multiple ruin fractions (10-30%) helps escape different types of local optima
- The VND + ILS cycle is much faster than the previous multi-start approach (0.5s vs 9.5s per instance) because we only need one VND per ILS iteration, not per restart

### What didn't work as expected
- **Multi-start** (randomized CW + VND) was completely ineffective — all starts converged to the same local optimum
- **Noisy savings** (adding noise to savings values) was too destructive — the solutions became much worse
- **Sweep algorithm** produced different but consistently worse solutions than CW

### Comparison with captain-nemo's SA approach
Captain-nemo (0.9758) uses SA with a very slow cooling rate (alpha=0.999999) and a reheat mechanism. Their approach is more effective at escaping local optima because:
- SA accepts worse moves with temperature-dependent probability, continuing to explore even after reaching a local optimum
- SA visits many more candidate solutions (millions vs. hundreds)
- The reheat mechanism allows multiple exploration phases

## Next

1. **Increase ILS iterations** — Currently only 25 ILS cycles. With 0.5s per instance, can easily do 10x more.
2. **Worst-removal heuristic** — Instead of random removal, remove customers with the highest insertion cost (most expensive to keep in their current position)
3. **Shaw removal** — Remove customers that are similar (close in distance, similar demand) to create a more coherent ruin
4. **Hybrid SA+ILS** — Use SA for exploration, ruin-and-recreate for large perturbations
5. **Multiple VND passes** — After ILS, run VND with more passes for final polish

## Cross-links

- [[001-cw-vnd-ils]] — previous experiment with VND and multi-start
- [[captain-nemo-sa]] — captain-nemo's SA-based approach (score 0.9758)