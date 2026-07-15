---
creator: captain-ahab
created: 2026-07-15T01:45:00
type: experiment
name: 004-adaptive-shaw-ils
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T18:41:10.571482+00:00'
---

# Experiment 004: ILS with Shaw Removal and Adaptive Strategy Selection

## Hypothesis

Adding Shaw removal (remove customers related by distance and demand) and adaptive strategy selection (track success rates, select strategies probabilistically) will improve the ILS by providing more diverse and targeted perturbations.

## Design

- **Phase 1:** Clarke-Wright deterministic construction + VND (10 passes)
- **Phase 2:** ILS cycle with adaptive strategy selection
- 4 ruin strategies: random, worst-removal, route-removal, Shaw removal
- 8 ruin fractions: 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30
- Adaptive selection: track success rate over episodes of 10 iterations, use softmax-weighted selection
- Full time budget (~9.5s/instance)

### Shaw removal
- Relatedness = w * (1 - d(i,j)/max_dist) + (1-w) * (1 - |d_i - d_j|/demand_range)
- w = 0.5 (equal weight for distance and demand)
- Pick seed customer, iteratively remove the most related customer

## Results

| Metric | Eval #3 (3 strategies) | Eval #4 (4 strategies + adaptive) |
|--------|----------------------|----------------------------------|
| Score | 0.9812 | 0.9826 |
| Mean gap | +1.95% | +1.80% |
| Best gap | 0.00% (1 instance) | 0.00% (2 instances) |
| Worst gap | 8.53% | 6.73% |
| Time | 475.6s | 475.5s |

Improvement: **+0.14%** in score, **-0.15pp** mean gap.

### Best instances (hidden set)
| Instance | Gap |
|----------|-----|
| G100_2344_01 | 0.00% |
| G100_3226_01 | 0.00% |
| G100_1212_01 | 0.01% |
| G100_2224_01 | 0.05% |
| G100_1211_01 | 0.10% |

### Worst instances (hidden set)
| Instance | Gap |
|----------|-----|
| G100_3344_01 | 6.73% |
| G100_1155_01 | 5.02% |
| G100_3256_01 | 4.70% |
| G100_3355_01 | 4.45% |
| G100_3173_01 | 4.45% |

## Analysis

### What worked
- **Shaw removal** adds a new dimension to the perturbation — it creates spatially coherent ruins that can be repaired effectively
- **Adaptive strategy selection** helps focus on strategies that are working well for the current instance
- The worst instance (G100_3344_01) improved from 8.53% to 6.73% — a meaningful improvement
- Two instances now match the reference exactly

### What didn't work as expected
- The improvements are getting smaller with each iteration — we're approaching the limit of the ILS approach
- The worst instances are still 4-7% away from the reference
- The adaptive selection might be converging too quickly to a single strategy

### Analysis of worst instances
The remaining worst instances might have specific characteristics:
- Very tight capacity constraints limiting route flexibility
- Clustered customer locations that are hard to optimize
- The reference might be closer to the true optimum, making it harder to match

## Next

1. **Multiple independent restarts** — Run the entire ILS from scratch with different seeds and pick the best. This provides more search diversity than a single long chain.
2. **Post-processing with targeted VND** — After the ILS, apply extra VND passes focused on the worst routes.
3. **Ruin-and-recreate with biased insertion** — Instead of cheapest insertion, try a regret-based insertion that considers the second-best option.
4. **Granular neighborhoods** — Only consider moves between close customers to speed up the VND.

## Cross-links

- [[003-ils-multiple-ruin-strategies]] — previous experiment with 3 strategies
- [[captain-nemo-sa]] — captain-nemo's SA-based approach