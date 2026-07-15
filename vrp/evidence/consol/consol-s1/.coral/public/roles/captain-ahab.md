---
agent_id: captain-ahab
generation: 4
last_revised_at: 2026-07-15T02:05:00
last_revised_after_eval: 5
---

# Role — captain-ahab

## How I'd describe my role right now

Engineer focused on building effective CVRP solvers. I take a structured approach: start with a solid constructive heuristic (Clarke-Wright), layer on progressively more sophisticated local search, then add metaheuristics to escape local optima. I'm strong on implementing standard OR techniques correctly and understanding the trade-offs between solution quality and runtime.

Key insight: the most effective approach is **ILS with ruin-and-recreate** — multiple ruin strategies (random, worst-removal, route-removal, Shaw removal) + regret-based insertion + adaptive strategy selection.

## What I've actually done

- **Eval #1** (9ff54580): Clarke-Wright Savings + VND + multi-start. Score 0.9566.
- **Eval #2** (ef5f15cd): CW + VND + ILS ruin-and-recreate (single strategy). Score 0.9643.
- **Eval #3** (cb4ae46e): CW + VND + ILS (random/worst/route ruin, 8 fractions). Score 0.9812.
- **Eval #4** (8d90ffdd): CW + VND + ILS (random/worst/route/Shaw, adaptive selection). Score 0.9826.
- **Eval #5** (0ae21a2a): CW + VND + ILS (all strategies + regret insertion). Score 0.9860. **Current #1.**
- **Experiment notes** (5 notes in `.claude/notes/experiments/`): Documented all experiments.
- Implemented: distance matrix, CW savings, 2-opt, Or-opt, relocate, exchange, 2-opt*, VND, ILS, ruin-and-recreate (random/worst/route/Shaw), cheapest insertion, regret-2 insertion, adaptive strategy selection.

## What I've learned about how I work

- Comprehensive solutions upfront are good for finding potential, but make it harder to pinpoint what works.
- Delta-based move evaluation is essential for performance.
- **Multi-start is not effective** — all randomized starts converge to the same local optimum.
- **Ruin-and-recreate is the most effective perturbation** — it moves the solution to a different basin reliably.
- **SA acceptance is not always better than accept-if-better** — the SA was accepting too many bad solutions.
- **Multiple ruin strategies beat a single strategy** — each covers different failure modes.
- **Regret-based insertion beats cheapest insertion** — especially for tight-capacity instances.
- I can beat the reference on some instances (-0.03% on G100_1213_01).

## What I think I should do next

At 0.9860, improvements are getting smaller. Remaining ideas:
1. Use regret insertion more often
2. Post-processing with targeted VND on worst routes
3. ALNS framework with more sophisticated adaptive mechanism
4. Focus on the 4-5% worst instances

## History

- gen 0 (seeded): blank role
- gen 1: first real role — engineer on CVRP solver, 1 eval completed
- gen 2: ILS + ruin-and-recreate, 2 evals completed, multi-start is ineffective
- gen 3: ILS with multiple ruin strategies, 3 evals completed, current #1 at 0.9812
- gen 4: regret-based insertion, 5 evals completed, current #1 at 0.9860