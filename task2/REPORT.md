# Task 2 — CORAL on a Combinatorial Optimization Problem: Job-Shop Scheduling

**Result: CORAL improved the naive seed by +33.1% and beat a classical tabu-search
baseline given twice its compute budget.**

| Method | Budget | Score | Gap vs lower bound |
|---|---|---|---|
| LWKR dispatch | — | 0.508241 | 97.17% |
| **Seed (FIFO dispatch)** | — | **0.542412** | 84.83% |
| LPT dispatch | — | 0.543713 | 84.48% |
| SPT dispatch | — | 0.603383 | 66.22% |
| MWKR dispatch (best simple rule) | — | 0.637649 | 56.89% |
| Tabu reference (Giffler-Thompson + Nowicki-Smutnicki N5) | 10 s/inst | 0.696170 | 43.64% |
| Tabu reference | 20 s/inst (2×) | 0.705115 | 41.82% |
| **CORAL best (eval 14)** | 10 s/inst | **0.721879** | **38.53%** |
| Lower bound (provably unattainable) | — | 1.000000 | 0.00% |

CORAL beats the same-budget tabu reference by **+3.69%** and the double-budget one by
**+2.38%**. Twelve real evaluations, two agents, 121 minutes wall clock.

## The task

Classic JSSP: `n` jobs × `m` machines, each job an ordered chain of one operation per
machine. Minimise makespan subject to job precedence and machine disjunction. The agent
writes `solve(machines, durations, time_limit, seed) -> starts`; the grader re-derives
the makespan itself rather than trusting a reported value.

**Score = mean over 9 hidden instances of `lower_bound / makespan`**, where
`lower_bound = max(busiest machine's total load, longest single-job chain)`.

### Why a lower bound and not the optimum

CP-SAT proves optimality on a 15×15 instance in ~10 s and a 30×15 in 58 s, but cannot
close a 30×20 in 240 s — and the hidden instances run to 10,000 operations. Exact optima
are unavailable at this scale. The lower bound is exact, instantly computable and
provably unbeatable, so the score sits in (0, 1] — but it is **not tight**: even an
optimal schedule scores below 1.0. The score is therefore a *relative* measure only.

CORAL's own agent independently confirmed this, measuring the bound as loose by
**8.5–20%, size-dependently** (`result/notes/experiments/eval-9-...md`). So the reported
38.53% gap overstates the true distance from optimality.

### Why square instances (jobs ≈ machines)

The hidden set is 3 × 20×20, 3 × 50×50, 3 × 100×100. Hardness peaks when the two trivial
bounds are balanced. When jobs ≫ machines the machine-load bound dominates and the
problem collapses:

| Size | jobs/machines | LB | FIFO seed | Tabu (10 s) |
|---|---|---|---|---|
| 200×8 | 25.0 | 10317 | 10596 (+2.70%) | **10317 (+0.00%)** in 0.6 s |
| 100×8 | 12.5 | 5338 | 5956 (+11.58%) | **5338 (+0.00%)** in 0.6 s |
| 50×10 | 5.0 | 2784 | 3297 (+18.43%) | **2784 (+0.00%)** in 0.6 s |
| 20×15 | 1.3 | 1158 | 1991 (+71.93%) | 1419 (+22.54%) |
| 20×20 | 1.0 | 1225 | 2172 (+77.31%) | 1666 (+36.00%) |

At 200×8 the busiest machine is saturated end-to-end, the tabu search reaches the bound
**exactly** in 0.6 s, and there is nothing left to optimise. Realistic for a factory
floor; useless as a benchmark.

## Data provenance

Two strictly separated sources.

* **Visible development instances** (`seed/instances/`): 6 instances, same generator and
  same three shapes as the hidden set, different seeds, with exact lower bounds. Plus
  `seed/benchmarks/`: ten classic OR-Library instances (ft10, la21, ta01, …) with
  *published* optima, downloaded from JSPLIB, for literature calibration.
* **Hidden scoring instances** (`taskdata/`, copied to `.coral/private/`): 9 instances
  **generated locally** with Taillard's (1993) scheme (durations ~ U[1,99], uniformly
  random machine order per job) under fixed seeds.

The hidden set is generated, not drawn from a benchmark library, because **the agent has
web access**. Given `la19` it could fetch the instance, fingerprint it, and emit a
memorised optimal schedule — scoring perfectly without writing a solver, exactly as the
Task 1 agent embedded precomputed circle centres. That would make knowledge accumulation
irrelevant to the score and render Tasks 3 and 4 meaningless.

## Anti-gaming, and how it was verified

**1. Exact solvers are unreachable.** `TaskGrader.get_python_command()` normally switches
to `uv run --project <codebase>` when the agent's repo contains a `pyproject.toml` — one
committed file and the agent could `import ortools`, call CP-SAT, and win. `Grader`
overrides it to pin `sys.executable`, fixing the dependency surface to the grader venv.

Verified: with a `pyproject.toml` planted in the codebase it still returns the grader
venv; `ortools`, `pulp`, `cvxpy`, `mip`, `networkx`, `scipy` are all unimportable; numpy
is available.

**2. Feasibility is not tradeable for score.** Every violation fails the whole
evaluation. Each failure path was injected and confirmed — including a schedule that
satisfies precedence *exactly* while colliding on machines, to prove the disjunction
check is not shadowed by the precedence check:

| Injected fault | Grader response |
|---|---|
| Machines collide (precedence exact) | rejected — `machine 7 overlap: job 0 op 0 runs [0,68) …` |
| Precedence violated | rejected |
| Wrong output shape | rejected |
| `solve()` raises | rejected |
| `import ortools` | rejected — `ModuleNotFoundError` |
| Valid seed schedule | accepted, makespan 2299 |

A further guard fails the eval if any makespan comes in *below* the lower bound — which
can only mean the validator is broken or an instance was mutated.

**3. The winning solver was audited.** `result/best_solution.py` (821 lines) imports only
`time` and `numpy`. No subprocess, no filesystem, no network, no reference to `taskdata`,
`private`, or `lower_bound`.

## Determinism

`time_limit` is wall-clock, so a solver's iteration count can depend on CPU load. Measured
on the **actual solver CORAL produced**, re-run twice under the grader's exact protocol:

```
repeat 1: score = 0.721561
repeat 2: score = 0.721440
spread    = 0.000121   (0.017% of score)

CORAL improvement, eval 1 -> eval 14 = 0.026957
signal / harness-noise               = 223x
```

The noise floor is two orders of magnitude below the effect being measured, so Task 3's
mean ± std comparisons will be able to resolve real differences.

This was not free. The *first* version of this task used a wall-clock limit on small
instances and was measurably nondeterministic — identical seed and instance produced
makespans `[1347, 1344, 1328]`, a 1.4% swing. See "Superseded run" below.

## Trajectory

Full data in `result/trajectory.csv`.

| Eval | Agent | Score | Gap vs LB | Min | Status |
|---|---|---|---|---|---|
| 1 | captain-nemo | 0.694922 | 43.9% | 0 | improved |
| 2 | captain-ahab | 0.691639 | 44.6% | 10 | improved |
| 3 | captain-ahab | 0.702777 | 42.3% | 22 | improved |
| 4 | captain-nemo | 0.711058 | 40.6% | 30 | improved |
| 5 | captain-nemo | 0.715539 | 39.8% | 39 | improved |
| 6–9 | (both) | 0.7104–0.7107 | ~40.8% | 47–68 | regressed / tune |
| 10 | captain-nemo | 0.718810 | 39.1% | 71 | improved |
| 11 | captain-ahab | 0.714985 | 39.9% | 75 | improved |
| 12 | captain-ahab | 0.714667 | 39.9% | 90 | regressed |
| 13 | captain-ahab | 0.717102 | 39.5% | 114 | improved |
| **14** | **captain-nemo** | **0.721879** | **38.53%** | 121 | improved |

Auto-stopped on `max_real_attempts: 12` (evals 8 and 9 were `--tune`, which do not count).

Note that eval 1 already lands at 0.6949 — above MWKR and near the same-budget tabu
reference. Opus reproduces the literature-standard approach (Giffler-Thompson
construction + Nowicki-Smutnicki N5 tabu) essentially from memory. **The 12-eval budget
buys the last 0.027**, which is where the interesting engineering happens.

## Cross-agent knowledge transfer

Eval 5, by `captain-nemo`, is titled *"Adopt captain-ahab's non-delay construction"* —
one agent read the other's note in shared state and lifted a construction that had earned
`captain-ahab` a +0.011 gain two evals earlier. This is the exact mechanism Task 3's
Condition A ablates, observed working.

## A CORAL bug the agent found

`captain-ahab` wrote `result/notes/infra/grader-multiprocessing-pickling.md`, documenting
that the grader imports `solution` via an `importlib` spec, so `multiprocessing.Pool.map`
— which pickles its callable — raises `PicklingError: import of module 'solution' failed`.
It used `multiprocessing.Process` under `fork` instead, which inherits rather than pickles.
By its own account this "bit me silently for four evals."

The agent then *falsified its own optimisation*: parallel best-of-8 restarts helped at
20×20 and 50×50 but were a wash at 100×100 (8626 solo → 8694 with 8 workers), so it gated
parallelism to instances ≤ 2500 operations. The winning solver is single-process.

## Evidence for Task 4 (knowledge-base pathology)

Twelve evals across two agents produced **14 notes, 1504 lines**, plus an agent-authored
`jssp-calibrate` skill. Of the ten notes with a confidence field, **nine are
`status: confirmed, confidence: high`** and one is `untested / medium`. There is no
observed instance of a note being retracted, downgraded, or contradicted — even though
eval 12 regressed and evals 6–9 produced no gain.

Combined with the Task 1 finding — where the agent wrote a **fabricated seed baseline**
("~0.57", true value 0.364102) into shared knowledge at `confidence: high, verified:
true` — this is the concrete failure mode Task 4 targets: claims enter the knowledge base
at uniformly high stated confidence and never leave.

## Superseded run

The first build of this task used easier instances (10×10 – 15×15, proven CP-SAT optima,
score = `optimum / makespan`). It was discarded after two evals:

* `captain-nemo` scored **0.997328** on eval 1, `captain-ahab` **0.997002** on eval 2 —
  a 0.27% mean gap with ten evals still to go. Every Task 3 ablation condition would have
  saturated near 0.999 and the mean ± std comparison would have measured nothing.
* The wall-clock `time_limit` was nondeterministic at those sizes (1.4% swing).

Rebuilt with square instances and lower-bound scoring. Harness noise fell from 1.4% to
0.017%. Archived under `superseded/` with its own README; that run's eval-1 tabu is
vendored as `tools/reference_solver.py` and used **only** to compute the reporting-only
`best_known` field, never for grading.

## Reproducing

```bash
git -C ../coral-upstream config core.autocrlf input   # see task1/REPORT.md, defect 1
cd task2
uv run --with numpy python tools/make_train_instances.py    # visible instances
uv run --with numpy python tools/make_hidden_instances.py   # hidden set + lower bounds
uv run --quiet python tools/baselines.py                    # the dispatching-rule ladder
uv run --project ../coral-upstream coral validate .         # seed scores 0.542412
uv run --project ../coral-upstream coral start -c task.yaml
uv run --project ../coral-upstream coral log
```

## Files

| Path | Contents |
|---|---|
| `task.yaml` | Task config: 2 agents, 12 evals, **no `score_threshold`** (equal budget per ablation condition) |
| `grader/` | Grader package: lower-bound scoring, feasibility validation, `sys.executable` pin |
| `seed/solution.py` | Naive FIFO dispatch seed (0.542412) |
| `seed/instances/`, `seed/benchmarks/` | Visible generated instances; classic benchmarks with published optima |
| `taskdata/` | Hidden instances + exact lower bounds (`grader.private`) |
| `tools/` | Instance generators, baselines, vendored reference solver |
| `result/best_solution.py` | The winning 821-line solver (eval 14) |
| `result/notes/` | All 14 notes the agents wrote to shared state |
| `result/trajectory.csv` | Per-eval scores, agents, timings |
| `superseded/` | The discarded easy-instance run and why |
