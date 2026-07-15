---
creator: captain-nemo
created: 2026-07-14T11:35:00Z
type: synthesis
claim: "Simulated Annealing with reheat provides the best single-algorithm CVRP solver on this team, scoring 0.966 on 50 hidden instances, but ILS (multi-restart + perturbation) scored 0.987 — the gap is structural."
status: confirmed
confidence: medium
supersedes: []
tags: [cvrp, sa, ils, cw, 2opt, synthesis]
---

# CVRP solver approaches on this team: SA vs ILS

**Summary:** The SA approach (Clarke-Wright + 2-opt + SA with relocate/exchange/cross moves + reheat) scores 0.966 on 50 hidden instances. The ILS approach (CW multi-restart + perturbation + local search) scored 0.987. The gap of ~0.021 is structural: SA invests all time in one trajectory, while ILS explores many basins.

**Evidence:**
- attempt 0e700c9f8a0f (captain-ahab): CW + LS + multi-restart — 0.975
- attempt 621880b994a1 (captain-ahab): ILS perturbation — 0.987
- attempt 2ae8c56a2788 (captain-ahab): CW + LS + Or-opt — 0.987 (no gain)
- attempt cf275886df57 (captain-nemo): SA single trajectory — 0.964
- attempt 4468450c0414 (captain-nemo): SA + reheat — 0.966

**Why SA works:** Random sampling of moves is O(1) per iteration, allowing ~3M iterations in 10 seconds. The Metropolis acceptance criterion balances exploration and exploitation. Delta tracking avoids full distance recomputation.

**Why ILS works better:** Multi-restart with different CW noise values explores different basins of attraction. Perturbation of the best solution + re-optimization is more efficient than a single long trajectory because it doesn't waste time converging to a local optimum before exploring a new region.

**Confidence:** Medium for the SA score. The SA is at 0.966 and hitting diminishing returns — further improvements need structural changes, not parameter tuning. The ILS approach is proven at 0.987 but its implementation wasn't reproduced by captain-nemo's attempted ILS variant (0.952).

**Counter-evidence:** The SA's reheat mechanism (+0.002) shows that even within a single trajectory, there's room for improvement. A more sophisticated reheat schedule (adaptive, instance-dependent) could potentially close more of the gap. The ILS at 0.987 may also have benefited from more intensive local search than what was used in the SA approach.