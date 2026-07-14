# R&D scratchpad

## task3_vrp — HGS-as-labeler validation (XML100)

Scripts: `task3_vrp/data/_labelval/`. Python: `/d/Libs/Miniforge2/python`. pyvrp 0.11.3, numpy 1.26.4, 16 CPUs.
Frozen ground truth: 10,000 XML100 instances + proven-optimal .sol from the same generator.

- [.sol integrity] ran audit_all_sols.py over ALL 10,000 .sol -> 91 (0.91%) are MALFORMED
  (a customer appears twice, e.g. XML100_1121_04 has cust 33 in Route #5 and #23).
  0 capacity violations. The 13 files whose `Cost` line disagrees with the grader formula
  are a strict SUBSET of those 91. -> excluded via corrupt_sols.txt.
- [rounding / scale] ran audit over the 9,909 CLEAN instances -> `.sol Cost` == grader-formula
  cost of the routes in that same .sol in 9909/9909 = 100.00%. Proven optima ARE on the
  grader's scale. (full population, not a sample)
- [rounding / pyvrp] ran verify_round.py -> pyvrp round_func='round' == grader int(sqrt+0.5)
  elementwise on 255,025 node pairs (25 instances), max|diff|=0. trunc 54.5%, dimacs 0.99%,
  exact 0.99%, none 1.66% -> all WRONG. Theory agrees: sqrt of an int is never exactly k+0.5
  ((k+.5)^2 = k^2+k+.25 is not an integer), so half-even (np.round) and half-up can't disagree.
- [rounding / end-to-end] ran HGS(round='round') on 8 instances, recomputed cost from the
  returned routes with the grader's own formula -> pyvrp cost == grader cost 8/8, exact.
- [fleet lower bound] ran fleet_analysis.py on the 9,909 clean -> k_opt == ceil(demand/cap) in
  8743 (88.23%); k_opt > k_min in 11.77%, excess up to +10 routes. By D: D=1 only 57.4%,
  D=6 99.9%. k_opt < k_min never (0). => k = ceil(demand/cap) is an UNSAFE fleet rule. VERIFIED.
- [bug found] common.solve_hgs did `int(res.cost())`; pyvrp returns math.inf when the best
  solution is infeasible -> OverflowError. This would have crashed exactly the pinned-fleet
  runs we need. Patched to return None + feasible=0.
- [sample design flaw] sample30.py used A=i%3+1, D=i%6+1 -> A is a deterministic function of D
  (perfectly aliased). Pooled gaps still valid (all levels present) but per-factor effects are
  confounded. Built sample30b.py (D blocked, A cycles within block) as a de-aliased replication.
- [grader fleet cap] grader parses n_vehicles from NAME via regex `-k(\d+)`, else dimension-1.
  XML-style names ("XML100_1111_11", "XML200_2145_01") have no `-k` -> cap = 100 = n-1, which is
  non-binding (100 customers => at most 100 routes anyway).
- [CORE: labeler quality] ran run_hgs.py, 420 runs (30 instances x {2,5,10,30}s x seeds{42,43,44}
  free-fleet = 360, plus 60 pinned) in 696s on 8 workers. Single-run seed=42, free fleet:
    2s -> 6.7% exact / mean 0.821% / max 1.939%
    5s -> 13.3% exact / mean 0.484% / max 1.299%
   10s -> 26.7% exact / mean 0.277% / max 1.149%
   30s -> 56.7% exact / mean 0.113% / max 0.620%
  NEGATIVE RESULT: HGS does NOT reliably reach the proven optimum. Even at 30s it misses ~43%
  of the time. Error magnitude is small though (mean +0.11%, max +0.62%).
  At equal CPU (30 cpu-s): single 30s run (56.7%/0.113%) BEATS best-of-3x10s (46.7%/0.150%).
  -> prefer one long run over seed multistart.
- [integrity] all 360 free runs: feasible, valid permutation, pyvrp cost == grader recompute. 0 exceptions.
- [PenaltyBoundWarning] fired ONCE, after the 360/420 progress line => during the PINNED phase only.
  It is pyvrp's "cannot find a feasible solution" diagnostic, and it fired on exactly the case we
  predicted: XML100_1371_27 pinned at k_min=29 when k_opt=33. No free-fleet run triggered it.
  Does NOT invalidate the core table.
- [fleet] free-fleet HGS: 360/360 feasible, max routes ever used = 34 (grader cap 100). k_hgs==k_opt
  in 30/30 at 10s. Pinning to k_min: 1/30 INFEASIBLE, and max gap among the feasible blows up to
  4.67% (vs 1.15% free) -> pinning hurts even when it works.
  HAZARD for k=k_ref: XML100_2272_02 -- HGS reproducibly finds 14-route solutions but the proven
  optimum uses 15 routes. k=k_ref=14 would EXCLUDE the true optimum. => prefer non-binding k.
- [cost] wall-clock/instance = budget + ~0.03s overhead (30s budget -> 30.03s mean, 30.06s max).
