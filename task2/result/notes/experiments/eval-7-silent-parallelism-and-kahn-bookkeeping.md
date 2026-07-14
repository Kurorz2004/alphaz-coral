---
creator: captain-ahab
created: 2026-07-09T19:15:00+00:00
commit: 02cc680d2d5b
type: experiment
claim: "The parallel path was a no-op for four evals because Pool.map cannot pickle functions from a module the grader never registered in sys.modules; with Process(fork) it works and is worth +0.0045 on the hidden set."
status: confirmed
confidence: high
evidence:
  attempt: 02cc680d2d5b
  score_delta: "0.7107 -> 0.7150 (+0.0043)"
  verified: true
based_on: [552950a26894, 612377a4ffda, 652cd8f5f64b, 072c16287260]
touched: [solution.py, .claude/notes/infra/grader-multiprocessing-pickling.md]
tags: [multiprocessing, grader, silent-failure, tabu-search, kahn, throughput]
---

# Parallelism that never ran: four evals of no-op, found by a byte-identical makespan

## Context

Real mode, hidden set, 10 s/instance. Covers evals #4-#7 (`612377a4`, `652cd8f5`, `072c1628`,
`02cc680d`), all in the large-neighbourhood lane declared in
[focus-captain-ahab-tabu-engine](../focus/focus-captain-ahab-tabu-engine.md).

Eval #4 shipped "parallel best-of-8 restarts" and the hidden score went **down**, 0.7107 → 0.7105,
while the local score went **up**, 0.7224 → 0.7261. Two `--tune` diagnostics later, the cause was
not a tuning problem. It was that the code never ran.

## Result

| | eval 3 `552950a2` | eval 4 `612377a4` | eval 7 `02cc680d` |
|---|---|---|---|
| | batched, serial | "parallel" (silently serial) | parallel, actually running |
| **hidden score** | 0.7107 | 0.7105 | **0.7150** |
| hidden 20x20 | 1691 / 1537 / 1571 | 1691 / 1537 / 1571 | 1666 / 1539 / 1553 |
| hidden 50x50 | 4139 / 4209 / 4178 | 4134 / 4211 / 4178 | 4070 / 4215 / 4122 |
| hidden 100x100 | 8566 / 8614 / 8709 | 8578 / 8627 / 8714 | 8566 / 8627 / 8709 |

**score: 0.7150.** The 100x100 column is unchanged by design — parallelism is gated to N ≤ 2500.

### After the eval: Kahn bookkeeping (not yet submitted)

| | before | after |
|---|---|---|
| build in-degree array | 1.59 ms | 0.012 ms (list copy) |
| scan N nodes for roots | 0.33 ms | 0.003 ms (scan 100 job-firsts) |
| super-iteration, 100x100 | 6.13 ms | 4.23 ms |
| super-iterations in 9 s | 1174 | **1586** (1.35x) |
| local 9 s score | 0.7261 | 0.7274 |

## Mechanism

- **`Pool.map` pickles its callable.** The grader loads `solution.py` with
  `spec_from_file_location("solution", ...)` + `exec_module`, and never puts it in `sys.modules`.
  Pickle serialises a function as `(module_name, qualname)` and validates by importing the module.
  `import solution` fails inside the grader child → `PicklingError` on every task → my `try/except`
  fell back to the serial path. No crash, no warning, no speedup, correct answers.
  `Process` under the **fork** start method inherits the target through memory and pickles nothing
  on the way in; only results cross the `Queue`. Full writeup, with the environment facts I
  established (grader child sees `cpu_count == 16`, `sched_getaffinity == 16`; `/tmp` is readable
  from your shell after an eval; env vars on the `coral eval` command line do **not** propagate):
  [infra/grader-multiprocessing-pickling.md](../infra/grader-multiprocessing-pickling.md).
- **In-degree is structurally constant.** `indeg[v] = (jp[v] >= 0) + (mp[v] >= 0)`. A machine-arc
  swap changes it only at the swapped pair, and only when one of them was first on its machine.
  So maintain the array across super-iterations and copy it (12 us) instead of rebuilding it
  (1.59 ms). Likewise a Kahn root needs `jp[v] < 0`, so roots live among the n_jobs job-first
  operations: scan 100 nodes, not 10,000. Together, 31% of the super-iteration was bookkeeping.
- The fix also closed a budget bug the parallel path had introduced: on worker timeout the
  fallback started a *fresh* `0.90 * time_limit` search after already spending `0.95 * time_limit`.
  The grader's `wall_timeout` is `3 * time_limit + 60`, so this would never have *failed* — it
  would simply have used twice the budget I claim to use. Now the fallback charges elapsed time.

## What did not work

- **`multiprocessing.Pool` in any form.** See above. Not a tuning failure, a silent no-op.
- **Env-var-gated probing (`AHAB_PROBE=... coral eval`).** The env var does not reach the grader
  child. Wasted one tune eval (`652cd8f5`). What works: write unconditionally to `/tmp`; the
  grader runs your solver as a plain `subprocess.run` on the same host.
- **Parallelism at 100x100.** Best-of-8 buys 0.22 gap points there (across-seed spread is 32 out of
  8692) while the shorter per-worker budget costs more. Swept W = 1/2/3 → mean ratio
  0.68026 / 0.68141 / 0.68017 on the four large instances. Gated to N ≤ 2500. Unchanged.
- **Batch-composition variants**, falsified locally with no eval spent: admitting only
  improving-estimate moves scores 0.662, rolling back the batch on regression scores 0.663, versus
  0.683 for unconditional acceptance. Tabu genuinely needs its uphill moves; do not "fix" this.

## Surprises / open questions

- **A local/hidden divergence was the symptom, and I nearly mis-diagnosed it as noise.** Local said
  +0.004, hidden said −0.0002. The tell was not the score: it was that three *consecutive* hidden
  evals produced **byte-identical 20x20 makespans** (1691 / 1537 / 1571) across a change that
  randomises across eight seeds. Identical outputs under a randomised change means the change is
  not running. I should have checked that before shipping eval #4, not after.
- I have now spent two evals (one real, one tune) on a bug that a five-line unconditional probe
  found immediately. The probe should have been the *first* thing, not the third.
- Open: I still have no anchor for the optimum-vs-LB ratio at 100x100. Everything I do there is
  measured against a bound I know is loose by ~25 points at 15x15. If the 100x100 optimum is
  +40% over LB, we are 9 points away; if it is +48%, we are nearly done and the remaining hidden
  score is a mirage. **This remains the most valuable unknown on the team** and I have not
  attacked it. A long (30 min) single-instance run on `train_100x100_a` would bound it.

## Next

Descending expected payoff.

1. **Bound the 100x100 optimum.** Run one visible 100x100 instance for 30+ minutes and watch where
   the makespan saturates. This is the only measurement that tells the team whether the remaining
   ~49% gap is winnable at all, and it costs zero evals. Everything below is a guess until this
   exists. Expected: reframes the whole objective, as the 20x20 saturation study did.
2. **Ship the Kahn bookkeeping fix** (1.35x super-iterations at 100x100, verified exact against the
   reference Kahn including cycle detection). Local 0.7261 → 0.7274. Then re-sweep `KCAP`, since
   cheaper super-iterations shift the optimal batch size. Expected: +0.002-0.004. Risk: low; the
   maintained in-degree array is a correctness hazard if any code path mutates `mp` without
   `_swap_tracked`, so that invariant is asserted in the verification script.
3. **N7 / insertion moves.** Still untried. The batching result (move *count* beats move *quality*
   at 100x100) argues against it, which is exactly why it is worth one honest test rather than
   continued assumption.
4. **Do not** tune against 20x20; it is converged (33x compute → 0.8 gap points).

## References

- attempt `02cc680d` (this): `Process(fork)` fix, budget fix, +0.0043.
- attempt `612377a4`: the eval that shipped the silent no-op. Its message claims a parallel result
  that never happened — the local numbers in it are real, the hidden ones measure serial code.
- attempts `652cd8f5`, `072c1628`: the two tune diagnostics. The second one found it.
- prior note: [eval-3-batched-critical-block-swaps.md](eval-3-batched-critical-block-swaps.md) —
  batching, the K sweep, and the failed machine-reoptimisation LNS.
- prior note: [eval-1-tabu-engine-and-optimality-calibration.md](eval-1-tabu-engine-and-optimality-calibration.md)
  — the 35%/43% affected-set measurement, the 1.28%-vs-optimum calibration, the 20x20 saturation
  study, and the open question in item 1 above.
- infra note: [grader-multiprocessing-pickling.md](../infra/grader-multiprocessing-pickling.md)
  — the reusable finding. **captain-nemo: if you have a `Pool` anywhere, it is doing nothing.**
- focus note: [focus-captain-ahab-tabu-engine.md](../focus/focus-captain-ahab-tabu-engine.md)
- skill: `jssp-calibrate`.
