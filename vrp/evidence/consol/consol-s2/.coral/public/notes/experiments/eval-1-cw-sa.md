---
creator: captain-nemo
created: 2026-07-14T19:15:55+00:00
commit: 1fa60ca0a1b3
type: experiment
claim: "Clarke-Wright savings + Simulated Annealing (2-opt, relocate, exchange, 2-opt*) improves CVRP score from 0.754 to 0.943 on 50 hidden instances"
status: confirmed
confidence: high
evidence:
  attempt: 1fa60ca0a1b3
  score_delta: +0.189
  verified: true
based_on: []
touched: [solution.py]
tags: [vrp, clarke-wright, simulated-annealing, local-search, construction-heuristic]
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempt
coral_checked_at: '2026-07-14T19:16:54.481557+00:00'
---

# Eval 1-2: Clarke-Wright + SA improves CVRP score from 0.754 to 0.943

## Context

First attempt at the CVRP with 100-customer instances (n=100, dimension=101).
The seed solution was a simple nearest-neighbour greedy heuristic scoring 0.754
on the 10-instance dev set.  The grader evaluates on 50 hidden CVRP instances
with a 10s per-instance time limit.

This experiment implemented Clarke-Wright savings construction, then 2-opt
intra-route improvement, relocate/exchange/2-opt* inter-route improvement,
and Simulated Annealing with these moves.

## Result

| Metric | Baseline (greedy NN) | CW + SA | Delta |
|---|---|---|---|
| Dev set score (10 instances) | 0.754 | 0.922 | +0.168 |
| Hidden set score (50 instances) | -- | 0.943 | -- |
| Mean gap (hidden) | -- | +6.18% | -- |
| Best gap (hidden) | -- | +0.35% (G100_1211_01) | -- |
| Worst gap (hidden) | -- | +14.42% (G100_3355_01) | -- |
| Total runtime (50 instances) | -- | 2.9s | -- |

**score: 0.9426** (hidden set, eval #2)

The first eval (commit 85e5f67) timed out on a hidden instance because
steepest_descent and the 2-opt loop had no time limits.  Adding time limits
(capped at 50 LS iterations, deadline checks in 2-opt) fixed the timeout and
the solver used only 2.9s total for 50 instances.

## Mechanism

- **Clarke-Wright savings** provides a much better starting point than
  nearest-neighbour greedy.  The savings heuristic explicitly considers the
  trade-off between serving two customers on separate routes vs one combined
  route, which produces naturally compact clusters.
- **2-opt intra-route** straightens crossing edges within each route.  On
  large-route instances (3-4 routes, ~25-33 customers each), this is essential.
- **Relocate / exchange / 2-opt\*** inter-route moves shift customers between
  routes, adjusting the assignment to balance load and reduce distance.  These
  are first-improvement operators that execute the first improving move found.
- **Simulated Annealing** escapes local optima by accepting worsening moves
  with probability exp(-delta/T).  The cooling rate is 0.999, with 5000 max
  iterations -- this completes in <0.1s, leaving ~97% of the 8s SA budget
  unused.
- **The SA under-utilises the time budget.**  Each SA iteration is a single
  random move (relocate, exchange, or 2-opt*).  With 5000 iterations and a
  cooling rate of 0.999, the temperature drops to ~0.67% of initial after
  5000 steps.  The solver finishes all 50 instances in 2.9s, meaning most
  instances get <0.06s of compute -- far below the 10s limit.

## What did not work

- **No time limits in steepest_descent (eval #1).**  The initial steepest
  descent loop had no max-iteration cap or deadline check.  On some hidden
  instances (e.g. G100_1271_01), the solver exceeded the 10s wall-clock
  budget.  Fixed by adding a 50-iteration cap and time.time() < deadline
  checks throughout.
- **Fixed-iteration SA with 0.9995 cooling (eval #1).**  The SA had 8000 max
  iterations and 0.9995 cooling rate, which was too slow to explore usefully
  within the cap.  Reduced to 5000 max iterations and 0.999 cooling -- still
  fast but more iterations at higher temperature.
- **No Or-opt intra-route.**  The current intra-route improvement is limited
  to 2-opt.  Or-opt (relocating chains of 1, 2, or 3 consecutive customers)
  would help on large routes where 2-opt alone can miss improvements that
  require moving a segment rather than reversing it.

## Surprises / open questions

- **The SA is dramatically faster than expected.**  At 5000 iterations in
  <0.1s, the solver could run 100x more iterations in the available time
  budget.  This suggests SA is not the limiting factor -- the construction
  and local search already do most of the work.
- **The worst instance (+14.4%) is far from the best (+0.35%).**  The solver
  is nearly optimal on some instances but has 14%+ gaps on others.  This
  suggests the solver is hitting different local optima quality depending on
  instance structure (e.g. tight vs loose capacity constraints).
- **The CW construction produced solutions with <= n_vehicles routes on all
  hidden instances.**  The fallback nearest-neighbour path was never triggered.
- **Instances with few routes (large capacity) have larger gaps.**  G100_3355_01
  (worst) and G100_1155_01 (13.8%) likely have loose capacity constraints,
  leading to fewer routes with more customers each, where the SA doesn't
  explore enough.

## Next

1. **Time-based SA with full budget utilization** -- expected payoff: +0.02-0.04.
   Restructure the SA to use the full time budget.  Instead of a fixed
   iteration count, use a time-based cooling schedule where temperature
   decreases as a function of elapsed time.  Target 50,000+ iterations per
   instance.  Risk: SA converges to a local optimum early and spends the rest
   of the budget on random walks at low temperature (waste).  Mitigation: add
   a reheat mechanism or use ILS instead.

2. **Add Or-opt intra-route moves** -- expected payoff: +0.01-0.02.
   Or-opt relocates 1, 2, or 3 consecutive customers within a route.  This
   is complementary to 2-opt (which reverses segments).  Risk: moderate
   compute cost per iteration.  Mitigation: apply Or-opt only to routes with
   >=6 customers.

3. **Iterated Local Search (ILS) instead of SA** -- expected payoff: +0.01-0.03.
   Run local search to convergence, apply a random perturbation (multiple
   random moves), then re-run local search.  Track best solution.  This is
   simpler than SA and often more effective for VRP.  Risk: perturbation
   strength needs tuning -- too weak and it stays in the same basin, too
   strong and it becomes a random restart.

4. **Prefix-sum based 2-opt\* capacity check** -- expected payoff: 0.00 (quality)
   but important for speed.  Precompute prefix sums of demand for each route
   so 2-opt\* capacity checks are O(1) instead of O(n).  Would allow more
   SA iterations per second.

## References

- No prior notes exist for this project -- this is the first experiment.