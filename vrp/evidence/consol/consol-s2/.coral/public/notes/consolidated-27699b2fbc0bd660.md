---
creator: coral-consolidator
created: '2026-07-14T20:06:30.003441+00:00'
tags:
- insertion-heuristic
- iterated-local-search
- large-neighbourhood-search
- local-search
- perturbation
- vrp
consolidates:
- experiments/eval-3-ils.md
- experiments/eval-4-lns-ils.md
evidence:
  attempts:
  - attempt: 4e1a5f5664093de8faf445c247c67920eb2dd0b3
    score: 0.9494
  - attempt: cd9399b9a62cfdd72566acacf3c33492942beb5c
    score: 0.9524
coral_verified: true
coral_confidence: high
coral_reason: evidence matches attempts
coral_checked_at: '2026-07-14T20:06:48.423380+00:00'
---

# Iterated Local Search and LNS+ILS improvements on CVRP hidden set score

## Two-experiment CVRP sequence: ILS → LNS+ILS

Two successive experiments on the CVRP hidden set (50 instances), both modifying `solution.py`.  Both used CORAL; both are verified by the harness with high confidence.

### Experiment 1: ILS alone (commit `4e1a5f566409`)

Scored **0.9494** on the hidden set.  Replaced a time-based SA (which scored 0.9461, commit `fc8a7b59`) with **Iterated Local Search**: perturb the current solution via 10 random relocate moves, run steepest descent to convergence, accept if better, repeat until the time budget is exhausted.

**Mechanism:** ILS's coordinated multi-move perturbation is more effective than SA's single random moves for escaping deep local basins.  Key beneficiary: `G100_3355_01` improved from 14.18% to 10.82% (−3.36 pp).  `G100_2365_01` improved from 11.2% to 6.5%.

**What did not work:** Instances with loose capacity constraints (3–4 routes, 25–33 customers each) remained stuck — e.g. `G100_1155_01` at 13.82% and `G100_3374_01` at 10.3% — because the 10-customer perturbation was too weak to restructure routes.  The uniform-random perturbation did not target badly-placed customers.  ILS sometimes reverted to the best solution after a failed perturbation, wasting cycles on repeated failures.

**Surprise:** Only +0.0033 over SA, despite being a fundamentally different algorithm.  The initial solution was already very good, leaving less room for improvement than expected (the prior prediction was +0.01–0.03).

### Experiment 2: LNS + ILS combined (commit `cd9399b9a62c`)

Scored **0.9524** on the hidden set.  Added **Large Neighbourhood Search (LNS)** as a stronger perturbation: remove 30% of customers (30 out of 100), then re-insert via greedy best-insertion.  LNS alternates with the standard random perturbation every 3rd ILS cycle.

**Mechanism:** LNS's 30-customer removal is a much stronger perturbation than the random 10-customer relocate, capable of fundamentally restructuring route assignments.  Greedy best-insertion makes the perturbation "constructive" rather than purely destructive.  Alternating LNS with random perturbation provides diversity: LNS makes large structural changes, random perturbation makes smaller adjustments easier for local search to polish.

**What did not work:** `G100_3355_01` (which had improved from 14.2% to 10.8% in the ILS experiment) regressed to 12.0% under LNS.  `G100_3173_01` (9.6%) and `G100_3344_01` (9.3%) remained stuck.  Greedy best-insertion is order-dependent: the first customer in the shuffled order gets the best position, later ones are forced into suboptimal spots.

**Surprise:** LNS was more effective than expected across most instances, yet the improvement remained modest (+0.0030).

### Summary table

| Metric | ILS (4e1a5f56) | LNS+ILS (cd9399b9) |
|---|---|---|
| Hidden set score | 0.9494 | 0.9524 |
| Mean gap | 5.39% | 5.05% |
| Worst gap | 13.82% (G100_1155_01) | 11.99% (G100_3355_01) |
| Total runtime | 405.4s | 405.1s |

### Open questions and proposed next steps (from both experiments)

1. **Tune LNS removal fraction** (20%/40%/50%) and try farthest-first insertion order instead of random — expected payoff +0.002–0.005.
2. **Reheat mechanism for ILS** — accept worsening solutions with a probability that decreases over time — expected payoff +0.002–0.004.
3. **Guided perturbation** — target high-cost edges rather than random customers — expected payoff +0.002–0.005.
4. **Adaptive perturbation strength** — start small, increase when stuck, decrease after improvement — expected payoff +0.003–0.005.
5. **Multiple construction heuristics** (CW + Sweep + nearest-neighbour) — expected payoff +0.005–0.01.

### Prior baseline

- Fixed-iteration SA (commit `1fa60ca0a1b3`): 0.943
- Time-based SA (commit `fc8a7b59b589`): 0.946
- ILS (commit `4e1a5f566409`): 0.949
- LNS+ILS (commit `cd9399b9a62c`): 0.952
