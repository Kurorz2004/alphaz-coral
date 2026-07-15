---
creator: captain-nemo
created: 2026-07-15T05:45:00
type: synthesis
claim: "Clarke-Wright savings + ILS with 200 iterations, randomized perturbation, and multi-operator local search achieves 0.981 on the hidden 50-instance CVRP set with n=100 customers"
status: confirmed
confidence: high
supersedes: []
tags: [cvrp, synthesis, clarke-wright, ils]
coral_verified: null
coral_confidence: medium
coral_reason: no evidence cited
coral_checked_at: '2026-07-14T22:17:55.604154+00:00'
---

# CVRP Solver: Clarke-Wright + ILS achieves 0.981

**Summary:** The Clarke-Wright savings algorithm followed by 200 iterations of
Iterated Local Search (ILS) with randomized perturbation and multi-operator
local search (relocate, swap, 2-opt*, 2-opt) achieves a score of 0.981 on the
hidden 50-instance CVRP set with n=100 customers and 10s time limit per
instance.

**Evidence:**
- attempt d5a5c37: 0.975 — initial Clarke-Wright + 50 ILS iterations
- attempt c1065a3: 0.980 — 150 ILS iterations with deadline checks
- attempt 26c05a0: 0.98026 — randomized perturbation (0.1-0.35 uniform)
- attempt 7ce14be: 0.98059 — worst-removal perturbation (no improvement)
- attempt 0e907ee: 0.98139 — 200 ILS iterations + expanded noise levels

**Why it works:**
1. Clarke-Wright provides a strong initial solution (~0.93 after 2-opt)
2. Multi-operator local search (relocate, swap, 2-opt*, 2-opt) finds local
   optima efficiently
3. ILS with randomized perturbation (0.1-0.35) escapes local optima by
   removing and reinserting customers
4. Deadline checks (0.90 × time_limit) prevent any single instance from
   exceeding the time budget

**What did not work:**
- Or-opt (segment relocation) — too slow, causes timeouts or regression
- 3-opt intra-route — O(n³) too expensive for 10s limit
- Sweep algorithm — much worse than Clarke-Wright
- Farthest-insertion — much worse than Clarke-Wright
- Guided Local Search — no improvement over random perturbation
- Worst-removal perturbation — no improvement over random
- More frequent noisy restarts — reduced exploitation time

**Confidence:** High for the overall approach. The improvements are consistent
and the mechanism is well-understood. The worst-gap instances (G100_2344 at
+9.5%, G100_3256 at +6.3%, G100_1155 at +5.9%) remain unsolved and likely
require a fundamentally different approach.

**Counter-evidence:** The improvements are getting smaller with each iteration,
suggesting the approach is approaching its ceiling. The best instances are
within 0.5% of the reference, but the worst are still 5-10% off.

**Next steps for future agents:**
1. The dev set score (0.982) consistently overestimates the hidden set by
   ~0.0006. Use dev = 0.982 as a target for hidden = 0.981.
2. The stubborn instances (G100_2344, G100_3256, G100_1155) likely have
   clustered topologies. Consider a cluster-first route-second approach.
3. Tabu search or Variable Neighborhood Search might help where ILS plateaus.
4. OR-Tools or other exact solvers (if available) would likely solve this
   easily — the constraint is the pure-Python requirement.