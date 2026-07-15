---
creator: captain-nemo
created: 2026-07-14T11:30:00Z
commit: 4468450c0414
type: experiment
claim: "SA with reheat when stalled improves score from 0.9637 to 0.9659 (+0.0022) on hidden instances"
status: confirmed
confidence: medium
evidence:
  attempt: 4468450c0414
  score_delta: "+0.0022 (from 0.9637 to 0.9659)"
  verified: true
based_on: [experiments/eval-4-simulated-annealing.md]
touched: [solution.py]
tags: [sa, reheat, relocate, exchange, cross]
---

# SA reheat when stalled: +0.0022 improvement

## Context

Eval #3 (0.9637) used a single SA trajectory with budget 70%. The SA converged to a local optimum but couldn't escape. Eval #4 adds a reheat mechanism: when the SA hasn't found a new best solution for 100K iterations, reset the temperature to 30% of the initial value. Also increased budget from 70% to 85%.

## Result

**Score: 0.965945** on 50 hidden instances (+0.0022). 421.1s total (8.4s/instance).

| Metric | Eval #3 | Eval #4 | Change |
|--------|---------|---------|--------|
| Overall score | 0.9637 | 0.9659 | +0.0022 |
| Mean gap | +3.82% | +3.59% | -0.23pp |
| Best gap | +0.25% | +0.24% | -0.01pp |
| Worst gap | +9.48% | +10.09% | +0.61pp (regression) |
| Instances < 1% | 4 | 4 | same |
| Instances > 7% | 5 | 5 | same |

Notable improvements:
- G100_1173: 4.6% → 2.8% (-1.8pp)
- G100_3163: 7.4% → 1.4% (-6.0pp — huge!)
- G100_3374: 9.5% → 6.4% (-3.1pp)

Notable regressions:
- G100_3344: 8.6% → 10.1% (+1.5pp)
- G100_3173: 4.4% → 7.6% (+3.2pp)

## Mechanism

The reheat mechanism resets `temperature = t0 * 0.3` every 100K iterations without a new best solution. This allows the SA to escape deep local optima by temporarily increasing the probability of accepting worsening moves. After the reheat, the temperature cools again, and the SA refines in the new region.

The reheat interval (100K iterations) and intensity (30% of t0) were chosen to balance exploration vs exploitation. Too frequent reheats would prevent convergence; too rare would never escape local optima.

The mixed results (some instances improve dramatically, others regress) suggest that:
1. The reheat helps on instances where the SA was stuck in a poor local optimum
2. On other instances, the reheat disrupts a productive convergence trajectory

## What did not work

- **Multi-start SA** — Running 5 SA trajectories with different CW seeds (each getting ~1.6s) scored 0.940, much worse than single-trajectory SA. Each restart didn't have enough time to converge.
- **ILS (steepest descent local search)** — CW + _improve_relocate/exchange/cross scored 0.952. The O(n^3) scanning is too expensive to do enough iterations.
- **Budget at 95%** — Failed eval due to timeout. Hidden instances are slower than dev instances.
- **Budget at 80%** — Used 349.5s/50 = 7.0s/instance. Safe.

## Surprises / open questions

- **Reheat helps some instances dramatically, hurts others** — G100_3163 went from 7.4% to 1.4% (best improvement), but G100_3344 went from 8.6% to 10.1% (worst regression). This suggests the reheat parameters are instance-dependent.
- **Time usage is 8.4s/instance** — Still well under the 10s limit. There's room for more iterations or more aggressive reheat.
- **The gap to captain-ahab's 0.987 is ~0.021** — The reheat closed some of the gap but not all. The remaining gap is likely structural (different algorithm, not just SA parameters).

## Next

In descending order of expected payoff:

1. **Tune reheat parameters** — Lower reheat intensity (0.15 * t0 instead of 0.3 * t0) and longer interval (200K instead of 100K). This should reduce the regressions while keeping the improvements. Expected: +0.001 to +0.003. Risk: low.

2. **Record-to-Record Travel** — Instead of SA's probabilistic acceptance, accept any solution within a threshold of the best. This is simpler and sometimes more effective for CVRP. Expected: +0.002 to +0.005. Risk: medium (requires re-architecting the SA loop).

3. **Increase budget to 90%** — The eval used 421.1s/50 = 8.4s/instance. Increasing to 90% adds ~0.6s. Expected: +0.001 to +0.002. Risk: low.

4. **Add 2-opt polish during SA** — Periodically run 2-opt on the best solution to ensure it's locally optimal. The SA might disrupt good route orderings. Expected: +0.001 to +0.003. Risk: low.

## References

- [experiments/eval-4-simulated-annealing.md](experiments/eval-4-simulated-annealing.md) — previous SA attempt (0.9637)
- [experiments/eval-1-clarke-wright-local-search.md](experiments/eval-1-clarke-wright-local-search.md) — captain-ahab's CW+LS approach (0.975)
- [experiments/eval-2-ils-perturbation.md](experiments/eval-2-ils-perturbation.md) — captain-ahab's ILS approach (0.987)