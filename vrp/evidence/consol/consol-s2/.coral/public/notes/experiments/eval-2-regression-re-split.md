---
creator: captain-ahab
created: 2026-07-15T00:30:00+00:00
commit: 24274aa1f9538c0a3e40c1310622d955b00e5544
type: experiment
claim: "Aggressive RRT perturbation (higher destroy_pct, larger deviation, random insertion, re-split) regresses score from 0.9933 to 0.9905"
status: confirmed
confidence: high
evidence:
  attempt: 24274aa1f9538c0a3e40c1310622d955b00e5544
  score_delta: "0.9933 → 0.9905; -0.0028"
  verified: true
based_on: [a7ac765]
touched: [solution.py]
tags: [cvrp, regression, rrt, perturbation]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T20:47:12.961311+00:00'
---

# RRT parameter regression: overly aggressive perturbation hurts score

## Context
After achieving score 0.9933 with a conservative RRT (deviation 1.5%, destroy 15-30%, 100 iterations), I tried to improve the worst instances by making the perturbation more aggressive. Changes:
- deviation: 1.5% → 5%
- destroy_pct: 15-30% → 30-50%
- Random insertion in regret-2 (20% probability)
- Re-split every 3rd RRT iteration
- Max iterations: 100 → 2000
- Random restarts: 50 → 20

## Result
| Metric | Best | This | Δ |
|---|---|---|---|
| Score | 0.9933 | 0.9905 | -0.0028 |
| Mean gap | +0.68% | +0.96% | +0.28pp |
| Worst gap | 2.91% | 3.07% | +0.16pp |

**score: 0.9905**

## Mechanism
- **Higher destroy_pct (30-50%)** destroys too much of the solution, making it hard for local search to recover.
- **Larger deviation (5%)** accepts too many worsening solutions, causing drift.
- **Random insertion in regret-2** adds noise that disrupts the effective regret-2 heuristic.
- **Re-split in RRT loop** wastes time — the super-route ordering preserves the original route structure.
- **Fewer random restarts (20 vs 50)** reduces diversity of initial solutions.

## What did not work
- **Aggressive RRT perturbation** — All changes together made the solver less effective. The conservative RRT was better.
- **Re-split during RRT** — The shortest-path re-split doesn't help because it preserves within-route ordering.
- **Random insertion** — Adding randomness to regret-2 made insertion worse, not better.

## Surprises / open questions
- The conservative RRT is better than the aggressive one. Expected the opposite.
- The 2.91% gap on the worst instance is hard to close.
- The giant tour construction might help but was added alongside aggressive changes — needs separate testing.

## Next
1. **Test giant tour construction alone** — Add only the giant tour + split to the best version. Expected payoff: +0.001-0.003. Risk: low.
2. **If giant tour helps, add to random restarts at 10-20% probability** — More diversity without sacrificing existing constructions.
3. **If giant tour doesn't help, try targeted perturbation for tight-capacity instances** — Focus on instances where routes are at capacity.

## References
- attempt a7ac765: best version (score 0.9933)
- [eval-1-multi-start-cw-sweep-rrt.md](eval-1-multi-start-cw-sweep-rrt.md): previous experiment note