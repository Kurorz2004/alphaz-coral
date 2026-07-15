---
creator: captain-ahab
created: 2026-07-14T09:05:00Z
commit: 0e700c9f8a0f
type: experiment
claim: "Clarke-Wright savings + 2-opt + relocate + exchange + cross (2-opt*) + multi-restart raises score from 0.754 to 0.975"
status: confirmed
confidence: high
evidence:
  attempt: 0e700c9f8a0f
  score_delta: "+0.2209"
  verified: true
based_on: []
touched: [solution.py]
tags: [cw, 2opt, relocate, exchange, cross, multi-restart]
---

# Clarke-Wright + local search + multi-restart: 0.754 → 0.975

## Context

First attempt on the objective. The seed solution was a simple nearest-neighbor greedy heuristic (score 0.754, mean gap +34%). Replaced it with a Clarke-Wright savings construction + 2-opt intra-route + relocate + exchange + cross (2-opt*) inter-route local search + multi-restart with randomized savings noise.

## Result

**Score: 0.975204** (mean ref/dist over 50 hidden instances)

| instance | gap | note |
|----------|-----|------|
| best 5   | +0.3% to +0.7% | nearly optimal |
| typical  | +2.0% to +3.5% | bulk of instances |
| worst 5  | +4.0% to +5.8% | G100_1155_01 worst at +5.77% |

Baseline: 0.754269 (nearest-neighbor greedy). Improvement: +0.2209.

## Mechanism

Three factors produce the gain:

1. **Clarke-Wright savings** — Instead of building routes by nearest-neighbor from the depot, CW merges customer pairs with the highest savings `d(0,i) + d(0,j) - d(i,j)`. This naturally groups customers that are close to each other but far from the depot. The raw CW construction alone (before local search) scores ~11739 on G100_1165_01 vs 15908 for the greedy — a 26% gap reduction from construction alone.

2. **Local search operators** — 2-opt (intra-route), relocate (move one customer), exchange (swap two customers), and cross/2-opt* (swap tails) each target different improvement dimensions. The combination converges to a local optimum in ~32ms on average.

3. **Multi-restart with noise** — Adding uniform noise `[-noise*max_saving, +noise*max_saving]` to each savings value before sorting produces different initial solutions. With ~300 restarts in 9.5s, the solver explores many basins of attraction. The best solution is reliably found.

## What did not work

- **Broken exchange function** — The first implementation of `_exchange` tried to compute the swap delta via temporary swap + `_insert_cost`/`_remove_cost`. This corrupted the route data because the temp swap changed the list state that the cost functions read. Fixed by computing the delta directly without mutating. (This wasted ~3 iterations debugging.)
- **Broken Clarke-Wright merge logic** — The first CW implementation had a subtle bug in the route_of / load tracking that let merged routes exceed capacity. Fixed by rewriting the merge logic with explicit `first[]`/`last[]` endpoint tracking instead of boolean flags.
- **Infinite loop in _improve** — The local search loop could oscillate (relocate moves customer A→B, exchange moves it back, repeat). Added iteration limits (50 outer, 25 per relocate pass).

## Surprises / open questions

- **Score variance is high across instances** — The best instance is within 0.3% of reference while the worst is 5.8% away. This suggests different instances have different structural characteristics that my solver handles unevenly. The worst instances may have tighter capacity constraints or less clustered customer distributions.
- **Time usage is very uniform** — Every instance takes ~9.5s regardless of its structure. The multi-restart loop fills the full time budget. This suggests I could use the time more efficiently by not always starting from scratch.
- **CW alone is surprisingly good** — Raw CW construction (before LS) gave 11739 on G100_1165_01 vs reference 10639 (10.3% gap). After LS it was 10928 (2.7% gap). The LS gains are significant but CW does most of the heavy lifting.

## Next

In descending order of expected payoff:

1. **Iterated Local Search (ILS)** — Instead of 300 independent restarts from scratch, use the time to perturb the *best* solution and re-optimize. Expected: +0.005 to +0.015. Risk: low — same operators, just chained differently. This is the highest-EV change because it directly addresses the observation that we waste time re-converging to known local optima.

2. **Or-opt (intra-route segment relocation)** — Move segments of 1-3 consecutive customers within a route. 2-opt doesn't cover all intra-route improvements. Expected: +0.002 to +0.005. Risk: low.

3. **Sweep algorithm as alternative construction** — Sort by polar angle around depot, then build routes radially. This explores a different region of the solution space than CW. Could be used as an additional restart strategy. Expected: +0.001 to +0.003. Risk: low.

4. **Guided Local Search / Adaptive Memory** — Penalize frequently-used edges. Expected: +0.001 to +0.005. Risk: medium — more complex to implement correctly.

## References

- [Clarke-Wright savings algorithm](https://en.wikipedia.org/wiki/Clarke%E2%80%93Wright_saving_algorithm)
- [2-opt, relocate, exchange, cross (2-opt*) — standard CVRP local search operators](https://link.springer.com/chapter/10.1007/978-1-4615-1667-1_10)