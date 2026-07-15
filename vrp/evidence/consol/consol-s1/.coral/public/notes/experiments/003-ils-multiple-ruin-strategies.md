---
creator: captain-ahab
created: 2026-07-15T01:30:00
type: experiment
name: 003-ils-multiple-ruin-strategies
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T18:41:10.571482+00:00'
---

# Experiment 003: ILS with Multiple Ruin Strategies

## Hypothesis

Different ruin strategies (random, worst-removal, route-removal) target different types of local optima. By cycling through multiple strategies, the ILS can escape a wider variety of local optima than with a single strategy.

## Design

- **Phase 1:** Clarke-Wright deterministic construction + VND (10 passes)
- **Phase 2:** ILS cycle: ruin-and-recreate + cheapest insertion repair + VND (10 passes)
- 3 ruin strategies: random, worst-removal (highest removal savings), route-removal (entire route)
- 8 ruin fractions: 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30
- Deterministic cycling through strategies and fractions (mod-indexed)
- Accept only if strictly better
- Full time budget (~9.5s/instance)

### Ruin strategies
- **Random:** Remove random customers
- **Worst-removal:** Remove customers whose removal gives the highest cost savings, with some randomness from the top candidates
- **Route-removal:** Remove an entire randomly chosen route

## Results

| Metric | Eval #2 (single ruin) | Eval #3 (multiple ruin) |
|--------|----------------------|------------------------|
| Score | 0.9643 | 0.9812 |
| Mean gap | +3.75% | +1.95% |
| Best gap | +0.20% | +0.00% (matched ref!) |
| Worst gap | +9.01% | +8.53% |
| Time | 25.8s (50 instances) | 475.6s (50 instances) |

Improvement: **+1.69%** in score, **-1.80pp** mean gap.

### Best instances (hidden set)
| Instance | Gap | Score |
|----------|-----|-------|
| G100_3226_01 | 0.00% | 1.0000 |
| G100_1211_01 | 0.10% | 0.9990 |
| G100_1212_01 | 0.10% | 0.9990 |
| G100_2252_01 | 0.10% | 0.9990 |
| G100_2111_01 | 0.10% | 0.9990 |

### Worst instances (hidden set)
| Instance | Gap | Score |
|----------|-----|-------|
| G100_3344_01 | 8.53% | 0.9214 |
| G100_3256_01 | 6.10% | 0.9425 |
| G100_1155_01 | 5.90% | 0.9443 |
| G100_3355_01 | 4.70% | 0.9551 |
| G100_2266_01 | 4.00% | 0.9615 |

## Analysis

### What worked
- **Worst-removal** is very effective — it removes customers that are expensive to keep in their current position, allowing the cheapest insertion to find a better arrangement
- **Route-removal** provides a strong perturbation that can completely reorganize a route
- **Multiple strategies** cover different failure modes: random for exploration, worst for exploitation, route for structural changes
- **Full time budget** (9.5s/instance) allows many ILS iterations (~500-1000)

### What didn't work as expected
- **SA acceptance** (tried between evals 2 and 3) was less effective than simple accept-if-better. The SA was accepting too many bad solutions.
- The worst instances (G100_3344_01, 8.53%) seem resistant to all strategies — these might have a fundamentally different structure (e.g., very tight capacity constraints)

### Comparison with captain-nemo's SA (0.9790)
My ILS approach (0.9812) now outperforms captain-nemo's SA (0.9790). The key difference is that ILS with ruin-and-recreate provides stronger perturbations that explore different basins more effectively than SA's random-walk approach.

## Next

1. **Adaptive ruin strategy selection** — Track which strategy is most successful and use it more often
2. **Shaw removal** — Remove customers that are related (close in distance, similar demand) for a more coherent ruin
3. **Multiple independent restarts** — Run the entire ILS from scratch with different seeds and pick the best
4. **Focus on worst instances** — Investigate G100_3344_01 to understand why it's resistant
5. **Post-processing** (after main ILS loop) — Apply additional targeted moves to close the remaining gap

## Cross-links

- [[002-ils-ruin-and-recreate]] — previous experiment with single ruin strategy
- [[captain-nemo-sa]] — captain-nemo's SA-based approach (score 0.9790)