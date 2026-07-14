# Task 1 — Replication: CORAL on `circle_packing`

**Result: CORAL reached the AlphaEvolve benchmark in 2 evaluations.**
Sum of radii **2.635983084918** (score **1.000002308**) vs. the benchmark 2.635977,
starting from a seed that scored 0.364102. Independently verified feasible at
machine precision.

## Why this task

Task 1 requires a "comparison table against the paper numbers." Only 11 tasks appear
in the paper's results tables. `spaceship_titanic` and `mnist` — the two most
approachable examples — are **not among them**, so no paper numbers exist to compare
against. `circle_packing` is in Table 1, with a clean single-agent Claude Opus row.

## Setup

| | |
|---|---|
| CORAL | `0.7.7.dev2+gc535d91a3` (upstream `c535d91`, editable clone) |
| Runtime | `claude_code`, **1 agent**, model `opus` (Claude Opus 4.8) |
| Preset | `local-claude` (tmux session) |
| Stop conditions | `score_threshold: 1.0` **or** `max_real_attempts: 25` |
| Grader | unmodified upstream `circle_packing_grader.grader:Grader` |
| Seed | unmodified upstream `seed/initial_program.py` |
| Run directory | `results/circle-packing/2026-07-09_205920/` |

### Deviations from the paper, and why

1. **`preset: local-claude` instead of `docker-opencode`.** The upstream `task.yaml`
   requires Docker + the OpenCode CLI + a LiteLLM gateway; none are available in this
   environment. The grader, seed, and benchmark constant are byte-identical to upstream.
2. **Single agent.** The paper's headline `circle_packing` row (Table 1) is a
   single-agent Claude Opus run. Its 4-agent row (Table 2) used **OpenCode + MiniMax
   M2.5** and reached only 2.5391 — comparing an Opus 4-agent run against that number
   would be meaningless.
3. **Opus 4.8, not 4.6.** The paper used Claude Opus 4.6. This is the one confound we
   cannot control for, and it plausibly explains our lower #Evals.

## Results

Score is `sum_radii / 2.635977`; higher is better. Baseline numbers are from the
paper's Table 1 (all single-agent, Claude Opus 4.6).

| Method | Sum of radii | Score | #Evals |
|---|---|---|---|
| Seed program (measured) | 0.959764 | 0.364102 | — |
| ShinkaEvolve | 2.6001 | 0.986389 | 62 |
| OpenEvolve | 2.6293 | 0.997467 | 100 |
| EvoX | 2.6320 | 0.998491 | 48 |
| **CORAL (paper)** | **2.6360** | **1.000009** | **11** |
| **CORAL (this run)** | **2.635983** | **1.000002** | **2** |
| AlphaEvolve (SOTA) | 2.635977 | 1.000000 | — |

### Per-eval trajectory

| Eval | Wall-clock | Score | Sum of radii | Grader time |
|---|---|---|---|---|
| — (seed) | — | 0.364102 | 0.959764 | — |
| 1 | +22 min | 0.998621 | 2.632342 | 0.1 s |
| 2 | +52 min | 1.000002 | 2.635983 | 0.2 s |

Auto-stop fired 66 s after eval 2 (`reason: score_threshold`). Total wall clock ~54 min.

**Wall-clock is dominated by the agent, not the grader.** Grading takes 0.1–0.2 s
against a 600 s timeout. The agent ran its own multi-minute basin-hopping searches
*outside* the graded call and embedded the resulting centers as constants, re-solving
the LP at call time. This is within the rules — the grader only calls `run()` and
checks the returned packing — but it means eval time measures nothing about optimizer
speed.

### Honest reading of "score > 1"

The grader prints `NEW RECORD!` for any score above 1.0. Our margin over the benchmark
is **+6.085e-06**, which is the same order as the rounding in the hardcoded constant
`BENCHMARK = 2.635977`. The defensible claim is that CORAL **matched AlphaEvolve to six
significant figures**, not that it set a new record.

Equally, **n = 1 on both sides.** Reaching the target in 2 evals vs. the paper's 11 is a
single sample of a stochastic process. The honest statement is "consistent with, and no
worse than, the paper," not "5× more sample-efficient."

## Verification

The grader tolerates constraint violations up to `1e-6`, and we beat the benchmark by
only `6e-6`. So the result was re-checked at machine precision (`verify.py`):

```
recomputed sum : 2.635983084918
score          : 1.000002308
margin vs bench: +6.085e-06

max wall violation : 0.000e+00
max pair violation : 6.106e-15      (grader tolerance: 1.000e-06)

distinct centers   : 26/26
min / max radius   : 0.069181 / 0.137010
margin / violation : 9.965e+08x

VERDICT: PASS
```

The worst violation is at machine epsilon, ~10⁹× smaller than the winning margin. The
score does not depend on grader slack.

Reproduce: `uv run --with numpy --with scipy python verify.py`

## What the agent actually discovered

The problem decomposes. For **fixed centers**, the optimal radii are the solution of a
linear program — maximize `sum(r)` subject to `r_i + r_j <= d_ij` and `0 <= r_i <= wall_i`,
all linear in `r`. The search collapses from 78 variables to 52, and the LP value becomes
an exact objective oracle over centers.

The seed misses this twice over: two of its 26 centers are *identical* (min pairwise
distance 0.0, forcing both radii to zero), and its greedy `compute_max_radii` is far from
the LP optimum. Solving the LP over the seed's own unmoved centers already yields 1.253635
(score 0.475587) — 0.29 of free score.

The agent found the decomposition on eval 1, then reported a genuine numerical insight in
its note: seeding SLSQP with the exact LP radii makes dozens of constraints active at the
start point, stalling the active-set QP. Starting from `0.5 x LP` radii gives 2.630 vs.
2.609 best-of-15 — "the single highest-leverage line." Eval 2 added population basin-hopping
over the LP-reduced landscape with a diverse elite archive, plus pinning BLAS threads to 1
for an 8× speedup.

Artifacts: `result/best_program.py` (77 lines), `result/agent-note-eval1.md`.
The agent also authored a reusable skill, `bilevel-packing-search`, into shared state.

## Defects found in CORAL

Three portability/correctness bugs surfaced while getting this to run. All are
reproducible and worth reporting upstream (see Task 6).

1. **`coral start` dies silently on a CRLF checkout.** `hatch-vcs` runs
   `git describe --dirty` to compute the version; on a Git-for-Windows clone read from
   WSL, every tracked file reads as modified (3,577/3,626), so the dirty check must hash
   them all — 50.8 s, over setuptools-scm's hardcoded 40 s timeout. Hatchling then
   re-raises the `TimeoutExpired` with the wrong arity, masking it as
   `TypeError: TimeoutExpired.__init__() missing 1 required positional argument: 'timeout'`.
   The manager aborts, the tmux session vanishes, and `.coral/public/logs/` is empty —
   the failure is undiagnosable from the error alone.
   *Fix applied:* `git config core.autocrlf input` (dirty check 50.8 s → 4.0 s).

2. **`workspace.setup` does not isolate dependencies.** `setup_worktree_env`
   (`coral/workspace/worktree.py:719`) sets `UV_PROJECT_ENVIRONMENT` intending a
   per-worktree venv — its docstring says this "prevent[s] concurrent agents from
   corrupting a shared venv." But **`uv pip install` ignores `UV_PROJECT_ENVIRONMENT`**
   (only `uv sync`/`uv run` honor it). With no `VIRTUAL_ENV` and no local `.venv`, uv
   walks `PATH` and installs into whatever venv it finds — here, CORAL's own. This run
   installed numpy 2.5.1 and scipy 1.18.0 into `coral-upstream/.venv`, neither a coral
   dependency, and created no worktree venv. Every `examples/*` task using
   `uv pip install` in `workspace.setup` is affected. With `agents.count > 1`, all agents
   race on one shared venv — exactly what the code claims to prevent.
   *Must be fixed before Task 3's multi-agent ablations.*

3. **`coral ui` cannot start without a Node toolchain, despite shipping prebuilt assets.**
   `_ensure_ui_built` (`coral/cli/ui.py:35-48`) rebuilds if any file under `web/src/` has
   an mtime newer than `coral/web/static/index.html`. On a fresh clone the checkout order
   makes `Overview.tsx` 2 s newer, so it always rebuilds — invoking `npm`, which here
   resolves to a Windows install that cannot run from Linux paths.
   *Fix applied:* touch the committed assets.

## Knowledge-accumulation failure mode (evidence for Task 4)

The agent's own experiment note, `result/agent-note-eval1.md`, records the seed baseline as:

> | sum of radii | ~1.5 (ring constructor) | 2.632342 | +1.13 |
> | score | ~0.57 | **0.998621** | +0.43 |

The seed's true values, measured before the run, are **0.959764** and **0.364102**. The
agent never evaluated the seed; it estimated. The guess was written into shared knowledge
with `status: confirmed` and `confidence: high`, and **nothing in CORAL will ever correct
it.** Downstream agents reading this note inherit a baseline that is off by 56%.

This is a concrete instance of the failure mode Task 4 targets: unverified claims entering
the knowledge base at high stated confidence, with no retraction or re-validation path.
Captured here from a 2-eval run; longer runs should compound it.

## Reproducing

```bash
git -C coral-upstream config core.autocrlf input     # required; see defect 1
cd task1
uv run --project ../coral-upstream coral validate .  # seed scores 0.364102
uv run --project ../coral-upstream coral start -c task.yaml
uv run --project ../coral-upstream coral log
uv run --with numpy --with scipy python verify.py
```

## Files

| Path | Contents |
|---|---|
| `task.yaml` | Task config (only the preset/agents/stop keys differ from upstream) |
| `grader/`, `seed/` | Byte-identical copies of `examples/circle_packing/` |
| `verify.py` | Standalone machine-precision feasibility check |
| `result/best_program.py` | The winning 77-line program (eval 2) |
| `result/agent-note-eval1.md` | The agent's experiment note (incl. the wrong baseline) |
| `result/auto_stop.json` | Stop record: `score_threshold`, score 1.0000023084, 2 attempts |
