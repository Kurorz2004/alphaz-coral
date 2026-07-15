---
creator: captain-ahab
created: 2026-07-15T00:25:00
type: experiment
name: 001-cw-vnd-ils
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T18:41:10.571482+00:00'
---

# Experiment 001: Clarke-Wright Savings + VND + ILS

## Hypothesis

The Clarke-Wright Savings algorithm, combined with variable neighborhood descent (2-opt, Or-opt, Relocate, Exchange, 2-opt*), will significantly outperform the nearest-neighbor greedy baseline. Multi-start (randomized savings) and Iterated Local Search (perturbation + VND) will further improve results by exploring different local optima.

## Design

Three variants tested:
1. **Variant A (eval'd):** Single deterministic Clarke-Wright + VND (full convergence) + multi-start randomized starts
2. **Variant B (on disk):** Clarke-Wright + Sweep + VND + ILS (perturbation cycle)
3. **Baseline:** Nearest-neighbor greedy (captain-nemo's submission)

### Key parameters
- VND neighborhoods: 2-opt, Or-opt (1/2/3 segments), Relocate (inter-route), Exchange, 2-opt*
- Multi-start: randomized block-shuffling of savings list (top 10% untouched, rest in blocks of 5)
- ILS: perturbation strength 5-20, VND re-optimization, accept-if-better

## Results

### Baseline (nearest-neighbor greedy)
| Metric | Value |
|--------|-------|
| Score | 0.7898 |
| Mean gap | +28.24% |
| Best gap | +1.61% |
| Worst gap | +54.40% |
| Time | 0.1s (50 instances) |

### Variant A (CW + VND + multi-start)
| Metric | Value |
|--------|-------|
| Score | 0.9566 |
| Mean gap | +4.59% |
| Best gap | +0.19% (G100_1211_01) |
| Worst gap | +9.36% (G100_2344_01) |
| Time | 477.8s (50 instances, ~9.5s/instance) |

Improvement: **+21.1%** in score, **-23.7pp** mean gap.

### Public dev instances (Variant A)
| Metric | Value |
|--------|-------|
| Score | 0.754 → 0.942 |
| Mean gap | +34.3% → +6.3% |

## Analysis

### What worked
- **Clarke-Wright Savings** provides a much better initial solution than nearest-neighbor
- **2-opt** is very effective for intra-route improvement — fast and high impact
- **Or-opt** (relocating 1-3 node segments) catches improvements 2-opt misses
- **Inter-route moves** (Relocate, Exchange, 2-opt*) are necessary but expensive

### What didn't work as expected
- **Multi-start** provides diminishing returns: the VND converges to the same local optimum from most randomized starts, regardless of the initial savings ordering
- **Simulated Annealing** (tried between variants) was too fast and didn't explore enough — 50k iterations in 0.1s but mostly random walks that don't improve
- **Time bottleneck:** The VND takes ~9.5s per instance, leaving almost no time for multi-start (~1-2 restarts per instance)

### Surprises
- The public instances (score 0.942) and hidden instances (0.957) have different difficulty profiles — the public set is harder
- Best gap on hidden instances is +0.19% — the algorithm is very close to the reference on some instances, suggesting the reference is achievable
- Worst gap of +9.36% on hidden instances — there's still room for improvement

## Next

1. **Optimize local search speed** — The VND spends most time in the 2-opt* and exchange neighborhoods. Ideas:
   - Use a granular neighborhood (only consider moves between customers that are close to each other)
   - Limit the number of VND passes (e.g., max 3 passes instead of full convergence)
   - Cache route loads rather than recomputing them

2. **Better ILS perturbations** — Instead of random moves, use directed perturbations:
   - Remove the worst customers from each route and re-insert them optimally
   - Use a ruin-and-recreate strategy (remove a set of customers, re-insert with cheapest insertion)

3. **Guided Local Search** — Add penalties to frequently-used edges to encourage exploration

4. **Multi-start with different construction heuristics** — Sweep algorithm might produce different initial solutions that lead to different local optima

5. **Tune cooling parameters** for SA — try slower cooling, higher initial temperature, and more iterations per temperature level

## Cross-links

- [[captain-nemo-baseline]] — baseline nearest-neighbor approach
- [[cw-savings-algorithm]] — Clarke-Wright savings algorithm reference