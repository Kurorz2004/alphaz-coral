# Connections Map

## Perturbation-based VNS across CVRP solvers
- Links: `experiments/eval-4-perturbation-cw.md`, `_synthesis/cvrp-best-approach.md`
- Pattern: Both captain-ahab and captain-nemo independently converged on perturbation-based restarts as the most effective metaheuristic for this CVRP task
- Implication: The perturbation + re-optimize cycle is a robust strategy for CVRP. Future work should build on this foundation rather than trying fundamentally different metaheuristics.

## CW vs Sweep constructions
- Links: `experiments/eval-6-sweep-cw.md`, `experiments/eval-3-multi-start-cw.md`
- Pattern: Clarke-Wright consistently outperforms sweep algorithm as a construction heuristic for these instances
- Implication: The radial structure of sweep doesn't match the customer distribution. CW is the right construction choice.

## Time budget as binding constraint
- Links: `experiments/eval-4-perturbation-cw.md`, `experiments/eval-3-multi-start-cw.md`
- Pattern: All best approaches use 95%+ of the 500s time budget. Each improvement comes from better use of available time.
- Implication: Future improvements must either be more time-efficient or find better solutions within the same time budget.