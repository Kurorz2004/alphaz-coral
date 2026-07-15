---
creator: captain-nemo
created: 2026-07-14T19:22:00+00:00
commit: fc8a7b59b589
type: experiment
claim: "Time-based SA with full budget utilization + Or-opt + prefix-sum 2-opt* improves CVRP score from 0.943 to 0.946 on 50 hidden instances"
status: confirmed
confidence: medium
evidence:
  attempt: fc8a7b59b589
  score_delta: +0.0036
  verified: true
based_on: [1fa60ca0a1b3]
touched: [solution.py]
tags: [vrp, simulated-annealing, time-based-cooling, or-opt, prefix-sum]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T19:30:50.474872+00:00'
---

# Eval 3: Time-based SA + Or-opt improves CVRP score from 0.943 to 0.946

## Context

Third attempt at the CVRP.  Eval #2 (commit 1fa60ca) scored 0.9426 with a
fixed-iteration SA (5000 iterations, 0.999 cooling) that used <0.1s per
instance, wasting 97% of the 8s time budget.

This experiment restructured the SA to use the full time budget with a
time-based linear cooling schedule, added Or-opt intra-route moves, and
used prefix-sum arrays for O(1) 2-opt* capacity checks.

## Result

| Metric | Previous (fixed-SA) | Time-based SA | Delta |
|---|---|---|---|
| Hidden set score (50 instances) | 0.9426 | 0.9461 | +0.0036 |
| Mean gap | 6.18% | 5.78% | -0.40% |
| Best gap | +0.35% (G100_1211_01) | +0.20% (G100_1212_01) | -0.15% |
| Worst gap | +14.42% (G100_3355_01) | +14.18% (G100_3355_01) | -0.24% |
| Total runtime | 2.9s | 404.2s | +401.3s |

**score: 0.9461** (hidden set, eval #3)

## Mechanism

- **Time-based SA** uses the full 8s budget per instance, applying hundreds
  of thousands of random moves instead of 5000.  The linear cooling schedule
  T = T_init * (1 - progress) gradually transitions from exploration to
  exploitation.
- **Or-opt** (relocating 1-3 consecutive customers within a route) finds
  improvements that 2-opt misses, especially on large routes (25-33
  customers).
- **Prefix-sum capacity checks** make 2-opt* capacity evaluations O(1)
  instead of O(n), saving compute per move.
- **The improvement is modest (+0.0036)** despite 100x more compute,
  suggesting the solution is near a local optimum for the current
  neighbourhood set.

## What did not work

- **Linear cooling schedule.**  Spends most of the time at low temperature,
  doing hill climbing rather than exploration.  A logarithmic or adaptive
  schedule might be better.
- **Or-opt as a low-frequency random move (10% of moves).**  Or-opt is too
  expensive to apply as a random SA move.  Better used as a deterministic
  post-processing step.
- **No improvement on worst instances.**  G100_3355_01 (14.2%) and
  G100_1155_01 (13.8%) barely improved, suggesting a local basin that
  these moves cannot escape.

## Surprises / open questions

- **The SA returns surprisingly small gains for 100x more compute.**
  The SA is doing millions of moves but finding very few improvements,
  suggesting the solution is already near a local optimum after the
  initial construction + local search.
- **The SA accepts very few moves at low temperature.**  With linear cooling,
  the last ~90% of the run is pure hill climbing on a near-optimal solution.
- **The prediction from eval-1 was +0.02-0.04 for time-based SA.**  Actual
  was +0.0036.  The mechanism was over-estimated — the SA was expected to
  find larger improvements but the solution was already near a local optimum.

## Next

1. **Iterated Local Search (ILS) instead of SA** — expected payoff: +0.01-0.03.
   Run local search to convergence, apply a strong perturbation (10-15 random
   relocate moves), then re-run local search.  Track best solution.  This
   should escape the local basins that the SA cannot.  Risk: perturbation
   strength needs tuning.

2. **Multiple construction heuristics (CW + Sweep)** — expected payoff: +0.005-0.01.
   Generate 2-3 initial solutions using different construction heuristics
   and pick the best one.  Different constructions have different structures
   and may lead to better local optima.

3. **Guided Local Search (GLS) penalties** — expected payoff: +0.005-0.015.
   Penalize frequently-used edges to force the search into new regions.

## References

- Prior eval: [eval-1-cw-sa.md](eval-1-cw-sa.md) — previous eval with fixed-iteration SA scoring 0.943
- The prediction from eval-1 Next #1 was: "Time-based SA with full budget utilization — expected payoff: +0.02-0.04."  Actual: +0.0036.  The mechanism was over-estimated.