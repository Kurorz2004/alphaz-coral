# Superseded run (easy instance set)

First Task 2 run, on the original hidden set (3x 10x10, 2x 15x10, 3x 15x15, proven
CP-SAT optima, score = mean(optimum/makespan)).

**Discarded because the task was too easy.** Agent `captain-nemo` scored 0.997328 on
eval #1 and `captain-ahab` 0.997002 on eval #2 — a 0.27% mean gap to optimum with 10
evals still to go. Every Task 3 ablation condition would have saturated at ~0.999 and
the mean +/- std comparisons would have measured nothing.

Calibration then showed:
  * Hardness peaks when jobs ~= machines. At 200x8 the machine-load bound is 16.6x the
    job bound and a tabu search hits it exactly in 0.6s — the problem is trivial.
  * The wall-clock `time_limit` made scores nondeterministic: identical seed and
    instance gave makespans [1347, 1344, 1328], a 1.4% swing.

The task was rebuilt with square 20x20 / 50x50 / 100x100 instances scored against an
exact lower bound. Harness noise on the new mixture is 0.0026 (0.38% of score) against
a seed->tabu signal of 0.16 — a 61x signal-to-noise ratio.

`agents/captain-nemo/solution.py` from this run (commit c6cbec41) is vendored as
`../tools/reference_solver.py` and used ONLY to compute the reporting-only
`best_known` field. It never participates in grading.
