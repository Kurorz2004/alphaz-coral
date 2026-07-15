---
creator: captain-ahab
created: 2026-07-14T10:30:00Z
commit: fbb900992193
type: experiment
claim: "Sweep construction heuristic regresses hidden-set score (-0.0032) — CW-only more robust"
status: refuted
confidence: high
evidence:
  attempt: fbb900992193
  score_delta: "-0.0032"
  verified: true
based_on: [experiments/eval-2-ils-perturbation.md]
touched: [solution.py]
tags: [sweep, diversity, dev-vs-hidden]
---

# Sweep heuristic: looked good on dev (+0.0025), regressed on hidden (-0.0032)

## Context

After eval #2 (0.9869) and eval #3 (0.9875), the remaining gap (~1.3%) needed structural diversity. The sweep algorithm (sort by polar angle, build routes radially) was added as an alternative to CW, interleaving 30 restarts between both methods.

On the 10 dev instances, the score improved from 0.9873 to 0.9898 (+0.0025). On the 50 hidden instances, it regressed from 0.9875 to 0.9843 (-0.0032).

## Result

**Score: 0.984266** (-0.0032 from eval #3, -0.0919 from baseline).

Worst regressions:
- G100_1155_01: +2.2% → +7.6%
- G100_3344_01: +5.1% → +6.4%
- G100_3374_01: -0.1% → +2.4% (was beating reference, no longer)

## Mechanism

The sweep algorithm produces different route structures than CW. On some instances (especially those with radially distributed customers) this helps. On others (clustered demand), sweep creates a worse starting structure that LS and ILS cannot fully repair.

The root cause: sweep doesn't account for savings — it groups by angle, not by distance efficiency. For many CVRP instances, CW's savings-based merging produces better initial routes.

## What did not work

- **Sweep + CW mixing** — The 30-restart budget was split between CW and sweep. This diluted the CW restarts, which were more robust.
- **Dev set is not predictive** — The dev set (10 instances) and hidden set (50 instances) have different structural distributions. An improvement on dev can hurt on hidden, and vice versa.

## Next

1. **Revert to CW-only** — CW construction is more robust across both sets. Revert the sweep changes.
2. **Random-insertion perturbation** — Instead of greedy re-insertion in the ILS phase, insert at random feasible positions. This creates more diverse solutions and may find new basins.
3. **Simulated Annealing** — Accept worsening solutions with decreasing probability in the ILS phase. Could help escape deep local minima.

## References

- [experiments/eval-2-ils-perturbation.md](experiments/eval-2-ils-perturbation.md)
- [experiments/eval-3-or-opt.md](experiments/eval-3-or-opt.md)