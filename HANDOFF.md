# Handoff — Alpha Z / CORAL assessment

Written for a fresh Claude Code session. Everything here is verified, not assumed;
where a number appears, it was measured. Task specification: [`TE M2-1.pdf`](./TE%20M2-1.pdf).

**Status:** Tasks 1 and 2 complete. Tasks 3–6 outstanding.

---

## 0. Read this before running anything

### Environment

| Tool | State |
|---|---|
| `uv`, `git`, `tmux`, `claude` | present |
| Docker, OpenCode, `srt`, Linux `node` | **absent** |
| CORAL | editable clone at `coral-upstream/` (gitignored), `0.7.7.dev2+gc535d91a3` |
| Agent binding | `claude-opus` → `claude_code` / `opus` (in `~/.config/coral/agents.yaml`) |

Because there is no Docker or OpenCode, any `examples/*/task.yaml` declaring
`preset: docker-opencode` (including `circle_packing`) **cannot run as-is**. Use
`preset: local-claude`.

### Mandatory one-time fix — `coral start` dies silently without it

```bash
git -C coral-upstream config core.autocrlf input
```

`coral-upstream/` was cloned by Git for Windows, so its working tree is CRLF while the
index is LF. Under WSL git, all ~3,577 tracked files read as modified. `coral start` →
`setup_grader_env()` → `uv pip install -e coral-upstream` → hatch-vcs → setuptools-scm →
`git describe --dirty`, which must then hash every "modified" file: **50.8 s**, over
setuptools-scm's hardcoded **40 s** timeout. Hatchling re-raises the `TimeoutExpired`
with the wrong arity, so it surfaces as a misleading

```
TypeError: TimeoutExpired.__init__() missing 1 required positional argument: 'timeout'
```

The manager aborts, the tmux session vanishes, and **`.coral/public/logs/` is empty** —
undiagnosable from the error alone. With the fix: dirty check 50.8 s → 4.0 s, install
41 s (failing) → 11 s (succeeding).

Symptom check: if `coral start` exits with no logs and an empty grader venv, run
`git -C coral-upstream status --porcelain | wc -l`. A count in the thousands means CRLF,
not a CORAL bug.

### You cannot launch `coral start` yourself

The auto-mode permission classifier blocks it — it spawns headless `claude` subprocesses
that run unattended with `--permission-mode auto`. **Ask the user to run it** with the
`!` prefix so output lands in the session:

```
! cd /mnt/d/Code/Fun/coral/task2 && uv run --project ../coral-upstream coral start -c task.yaml
```

`coral start` creates a **detached** tmux session and returns immediately. Read-only
commands (`coral status`, `coral log`, `coral show`, `coral notes`, `coral stop`) run fine.

### Gotchas that cost time

* **`pgrep -f "coral.cli start"` matches your own shell.** The pattern appears in the
  bash wrapper's command line, so it self-matches and you conclude the run is alive when
  it is dead (and vice versa). Use `ps -eo args | grep "[p]ython -m coral.cli start"`.
* **Attempt JSON uses `title`, not `message`.** A monitor doing
  `(d.get("message") or "").splitlines()[0]` raises `IndexError` on every attempt and
  silently emits nothing. Keys: `agent_id, commit_hash, feedback, metadata, parent_hash,
  parent_shared_state_hash, score, shared_state_hash, status, timestamp, title`.
* **`workspace.repo_path` and `results_dir` resolve against the process CWD**, while
  `grader.setup` resolves against the task dir. Run `coral start` from inside the task dir.
* **`coral ui`** works now (assets touched); it binds `127.0.0.1:8420` and takes ~90 s to
  come up because it walks the run dir over drvfs.

---

## 1. Repository layout

```
coral/
├── TE M2-1.pdf            task specification (6 tasks)
├── README.md              status board
├── HANDOFF.md             this file
├── coral-upstream/        editable CORAL clone (gitignored; becomes the Task 4 fork)
├── task1/                 circle packing — replication      [DONE]
│   ├── task.yaml  grader/  seed/  verify.py
│   ├── REPORT.md
│   └── result/            best_program.py, agent-note-eval1.md, auto_stop.json
└── task2/                 job-shop scheduling — OR problem   [DONE]
    ├── task.yaml  grader/  seed/  taskdata/  tools/
    ├── REPORT.md
    ├── result/            best_solution.py, notes/, trajectory.csv, auto_stop.json
    └── superseded/        discarded first build + why
```

Run outputs land in `taskN/results/<task-slug>/<timestamp>/` (gitignored).

---

## 2. Task 1 — Circle Packing (replication) — DONE

**Problem.** Pack N=26 circles in a unit square, maximize `Σ rᵢ`. Constraints: containment
and pairwise non-overlap, both at `1e-6` tolerance. Any violation ⇒ score **0.0**.
Timeout 600 s. Score = `sum_radii / 2.635977` (AlphaEvolve's result, hardcoded).

**Seed** (`seed/initial_program.py`): one circle at center, ring of 8 at r=0.3, ring of 16
at r=0.7, all clipped to `[0.01,0.99]`; radii from a greedy proportional-shrink. Broken
twice: clipping makes **two centers identical** (both radii → 0), and the greedy radius
assignment is far from optimal. Scores **0.364102** (sum 0.959764).

**Key structure.** With centers fixed, optimal radii are a **linear program**
(`max Σrᵢ s.t. rᵢ+rⱼ ≤ dᵢⱼ, 0 ≤ rᵢ ≤ wallᵢ`). Solving it on the seed's own unmoved centers
gives 1.253635 (score 0.475587) for free. The agent found this on eval 1.

**Result.** Single agent (Opus 4.8), stop at score ≥ 1.0 or 25 evals. Reached the target
in **2 evals**, 54 min.

| Method | Sum of radii | Score | #Evals |
|---|---|---|---|
| Seed | 0.959764 | 0.364102 | — |
| ShinkaEvolve | 2.6001 | 0.986389 | 62 |
| OpenEvolve | 2.6293 | 0.997467 | 100 |
| EvoX | 2.6320 | 0.998491 | 48 |
| **CORAL (paper, Table 1)** | **2.6360** | **1.000009** | **11** |
| **CORAL (our run)** | **2.635983** | **1.000002** | **2** |
| AlphaEvolve (SOTA) | 2.635977 | 1.000000 | — |

Baselines are the paper's Table 1 (single-agent Claude Opus 4.6). The paper's *Table 2*
4-agent circle_packing row used OpenCode + MiniMax M2.5 and reached only 2.5391 — never
compare an Opus multi-agent run against it.

**Two claims deliberately NOT made.** (1) The grader prints `NEW RECORD!`, but our margin
over the benchmark is **+6.085e-06**, the same order as the rounding in the constant
`2.635977`. We matched AlphaEvolve to six significant figures; we did not break a record.
(2) 2 evals vs 11 is n=1 vs n=1 on a stochastic process, with Opus 4.8 vs 4.6 as a
confound. The report says "consistent with, and no worse than, the paper."

**Verified feasible** (`task1/verify.py`, run it): max wall violation 0.0, max pairwise
overlap **6.106e-15**, i.e. ~10⁹× smaller than the winning margin. 26/26 distinct centers.

**Caveat worth knowing.** The agent ran its search *outside* the graded call and embedded
the winning centers as constants, re-solving the LP at runtime. Legal (the grader only
calls `run()`), but the 0.1 s eval time says nothing about optimizer speed.

---

## 3. Task 2 — Job-Shop Scheduling (our OR problem) — DONE

**Problem.** `n` jobs × `m` machines; each job is an ordered chain of one operation per
machine. Minimize makespan subject to job precedence, machine disjunction, no preemption.
Agent writes `solve(machines, durations, time_limit, seed) -> starts`; the grader
**re-derives the makespan itself**.

**Scoring.** `mean(lower_bound / makespan)` over 9 hidden instances, where
`lower_bound = max(busiest machine total load, longest single-job chain)`. Exact,
instantly computable, provably unbeatable ⇒ score ∈ (0,1]. **Not tight**: even an optimal
schedule scores < 1.0, so the score is *relative only*. (CORAL's own agent independently
measured the bound as loose by 8.5–20%, size-dependently.)

Why not proven optima: CP-SAT proves 15×15 in ~10 s and 30×15 in 58 s but cannot close
30×20 in 240 s. The hidden instances run to 10,000 operations.

**Data.**
* Hidden (`taskdata/`, → `.coral/private/`): 9 instances, **generated** with Taillard's
  1993 scheme (durations ~U[1,99], random machine order per job), fixed seeds.
  3× 20×20, 3× 50×50, 3× 100×100.
* Visible (`seed/instances/`): 6 instances, same generator/shapes, different seeds, with
  exact lower bounds. `seed/evaluate_local.py` scores against them for free.
* `seed/benchmarks/`: 10 classic OR-Library instances (ft10, la21, ta01, …) with
  *published* optima, from JSPLIB — literature calibration only.

Hidden instances are generated, **not** public benchmarks, because the agent has web
access: given `la19` it could fetch, fingerprint, and emit a memorized optimal schedule.
That is exactly what the Task 1 agent did with precomputed circle centers, and it would
make knowledge accumulation irrelevant to the score — destroying Tasks 3 and 4.

**Seed** (`seed/solution.py`): greedy non-delay list scheduling, FIFO priority (lowest job
index), ties by earliest possible start. Scores **0.542412** (84.83% over the bound).

**Result.** 2 agents (`captain-nemo`, `captain-ahab`), Opus, `max_real_attempts: 12`,
**no `score_threshold`**. 14 attempts (12 real + 2 `--tune`), 121 min.

| Method | Budget | Score | Gap vs LB |
|---|---|---|---|
| LWKR dispatch | — | 0.508241 | 97.17% |
| **Seed (FIFO)** | — | **0.542412** | 84.83% |
| LPT dispatch | — | 0.543713 | 84.48% |
| SPT dispatch | — | 0.603383 | 66.22% |
| MWKR dispatch | — | 0.637649 | 56.89% |
| Tabu reference (GT + Nowicki-Smutnicki N5) | 10 s/inst (same) | 0.696170 | 43.64% |
| Tabu reference | 20 s/inst (2×) | 0.705115 | 41.82% |
| **CORAL best (eval 14)** | 10 s/inst | **0.721879** | **38.53%** |
| Lower bound (unattainable) | — | 1.000000 | 0.00% |

**+33.1% over the seed**; beats the same-budget tabu by +3.69% and the double-budget tabu
by +2.38%. Regenerate any of these with `uv run --quiet python tools/baselines.py`.

**Anti-gaming (tested, not assumed).**
* `Grader.get_python_command()` is overridden to return `[sys.executable]`. Without it, a
  committed `pyproject.toml` flips execution to `uv run --project <codebase>` and the
  agent can `import ortools` and call CP-SAT. Verified: `ortools`, `pulp`, `cvxpy`, `mip`,
  `networkx`, `scipy` all unimportable; numpy available.
* Feasibility is not tradeable for score — any violation fails the whole eval. Injected
  and confirmed rejected: machine overlap (with precedence *exact*, to prove the
  disjunction check isn't shadowed by the precedence check), precedence violation, wrong
  output shape, `solve()` raising, `import ortools`.
* Guard: makespan < lower bound ⇒ hard fail (validator broken or instance mutated).

**Determinism (this is what makes Task 3 possible).** `time_limit` is wall-clock, so
iteration counts can depend on CPU load. Measured on **CORAL's own winning solver**,
re-run twice under the grader's exact protocol:

```
repeat 1 = 0.721561 ;  repeat 2 = 0.721440 ;  spread = 0.000121  (0.017% of score)
signal (eval 1 → eval 14) = 0.026957        ⇒  SNR ≈ 223×
```

---

## 4. Hard-won design lessons (do not relearn these)

1. **Saturation kills ablations.** The first Task 2 build used 10×10–15×15 instances with
   proven optima. Both agents scored ~**0.997 on eval #1**, with 10 evals to spare. Every
   Task 3 condition would have reported `0.999 ± 0.001`. Rebuilt with square instances +
   lower-bound scoring. The superseded run is kept in `task2/superseded/`.
2. **Many jobs, few machines is EASY, not hard.** At 200×8 the machine-load bound is
   **16.6×** the job bound, the busiest machine saturates, and a tabu search reaches the
   bound **exactly in 0.6 s**. Even naive FIFO is only 2.70% off. Hardness peaks at
   jobs ≈ machines (balanced bounds). Verified at 200×8, 100×8, 50×10, 20×15, 20×20.
3. **Wall-clock budgets are nondeterministic.** On the *easy* instances, identical seed +
   instance gave makespans `[1347, 1344, 1328]` — a 1.4% swing, larger than the ablation
   effects we want to detect. Mitigated by averaging 9 mixed-size instances (noise 0.017%).
   Counterintuitively the *large* instances are the quiet ones (100×100 spread = 0); 20×20
   is the noisy one, and dropping it made things worse.
4. **A first eval that looks like a triumph is a red flag.** Both Task 2 agents hit 0.997
   immediately; that was the harness being too easy, not the agents being brilliant. Read
   the diff before believing a leap.

---

## 5. CORAL defects found (material for Task 6)

| # | Defect | Status |
|---|---|---|
| 1 | **CRLF ⇒ `coral start` dies with no logs.** `git describe --dirty` (hatch-vcs → setuptools-scm) exceeds a hardcoded 40 s timeout; hatchling then masks `TimeoutExpired` as an unrelated `TypeError` by re-raising it with the wrong arity. | Worked around (`core.autocrlf=input`) |
| 2 | **`workspace.setup` does not isolate dependencies.** `setup_worktree_env` (`coral/workspace/worktree.py:690-720`) sets `UV_PROJECT_ENVIRONMENT` intending a per-worktree venv — its docstring (line 699) says this "prevent[s] concurrent agents from corrupting a shared venv." But **`uv pip install` ignores that variable**; with no `VIRTUAL_ENV` it walks `PATH` and installs into whatever venv it finds. Task 1's run put numpy 2.5.1 + scipy 1.18.0 into `coral-upstream/.venv` and created no worktree venv. Affects every `examples/*` task using `uv pip install` in `workspace.setup`. | Fixed in `task2/task.yaml` by running `uv venv` **first**; verified CORAL's venv stays clean. Upstream still broken. |
| 3 | **`coral ui` needs a Node toolchain despite shipping prebuilt assets.** `_ensure_ui_built` (`coral/cli/ui.py:35-48`) rebuilds if any `web/src/` file is newer than `coral/web/static/index.html`. A fresh clone stamps `Overview.tsx` 2 s later, so it always rebuilds — invoking `npm`, which here resolves to a Windows install unusable from Linux paths. | Worked around (touched the committed assets) |
| 4 | **Grader/multiprocessing pickling.** The grader imports `solution` via an `importlib` spec, so `multiprocessing.Pool.map` raises `PicklingError: import of module 'solution' failed`. `Process` under `fork` works. **Found by agent `captain-ahab`**, which said it "bit me silently for four evals." See `task2/result/notes/infra/grader-multiprocessing-pickling.md`. | Documented |
| 5 | **`agents.heartbeat: []` does not disable heartbeats — two separate regrowth paths.** (a) `_preprocess` (`config.py`) back-fills every default the user did not *name*; an empty list names nothing, so `heartbeat: []` in task.yaml regrows **all four** defaults. (b) `write_agent_heartbeat` / `write_global_heartbeat` re-inject `PROTECTED_LOCAL={reflect}` / `PROTECTED_GLOBAL={consolidate}` when absent, which bites even the dotlist form that bypasses (a). Silent in both cases. Workaround on stock CORAL: name all four with `every: 1000000` (`every: 0` raises `ZeroDivisionError`). | Both fixed on `task3-ablation`; two regression tests |
| 8 | **`SharingConfig` is dead config.** `sharing.attempts / notes / skills` (`config.py:315`) is a documented-looking switch for exactly the knowledge channel Task 3 ablates — and nothing in the entire `coral/` package ever reads `config.sharing`. Setting `sharing.notes: false` does nothing, with no warning. | Found, not fixed |
| 6 | **`agents.research` is dead in multi-agent mode.** `generate_coral_md` computes `research_section`, `workflow_summary` and the step-number offsets, but `coral.md.template` contains none of those placeholders — only `coral_single.md.template` does. `str.format` ignores the extra kwargs, so `agents.research: false` silently does nothing for any run with `agents.count > 1`. | Found, not fixed (out of Task 3 scope) |
| 7 | **Disabling heartbeats also disables the eval-result header.** `manager.py`'s `if not actions: continue` sits above the code that builds the `## Eval #N Results` block, so the two features are coupled: no heartbeat action ⇒ no injected score summary. Defensible, but undocumented, and it confounds any "disable heartbeats" ablation. | Documented; measured in `task3/analyze.py` |

---

## 6. Evidence already collected for Task 4

Task 4 requires "at least one concrete failure mode in CORAL's current notes/skills
system, with evidence from your Task 2 or Task 3 runs." We have two:

* **Fabricated claim at high confidence (Task 1).** `captain-nemo`'s note
  (`task1/result/agent-note-eval1.md`) records the seed baseline as *"~1.5 / score ~0.57"*.
  The measured truth is **0.959764 / 0.364102**. The agent never ran the seed; it guessed,
  and wrote the guess into shared state with `status: confirmed, confidence: high,
  verified: true`. Nothing in CORAL can retract it. Attempt hash `b7beb589890f`.
* **Uniform, never-revised confidence (Task 2).** 12 evals × 2 agents → **14 notes,
  1504 lines** (`task2/result/notes/`). Of the ten notes with a confidence field, **nine
  are `status: confirmed, confidence: high`**; one is `untested / medium`. Nothing was ever
  retracted or downgraded — not after eval 12 regressed, not after evals 6–9 produced no
  gain.

Positive control (the thing an ablation should destroy): **cross-agent transfer is real.**
Task 2 eval 5 is titled *"Adopt captain-ahab's non-delay construction"* — one agent read
the other's note in shared state and lifted a construction worth +0.011.

---

## 7. Next: Task 3 (ablation)

Spec: same task as Task 2. Condition **A** = disable notes/skills. Condition **B** =
disable all heartbeats. Each condition ≥ 3 runs; report mean ± std of Final Score, vs full
CORAL.

**Run budget already set correctly:** `task2/task.yaml` uses `max_real_attempts: 12` and
deliberately **no `score_threshold`**. Every condition must spend an identical eval budget
or the means are incomparable. Do not add a score threshold.

**~~Condition B is free~~ — the recipe is wrong, though a config-only route exists.**
Setting `agents.heartbeat: []` does **not** disable heartbeats. Two independent
mechanisms regrow it, and both must be defeated:

1. `_preprocess` (`coral/config.py`) back-fills every default action the user did not
   *name*. An empty list names nothing, so **`heartbeat: []` in task.yaml regrows all
   four defaults** and is byte-identical to not setting it at all.
2. `write_agent_heartbeat` / `write_global_heartbeat` (`coral/hub/heartbeat.py`) re-add
   `PROTECTED_LOCAL={reflect}` / `PROTECTED_GLOBAL={consolidate}` whenever absent. This
   bites even the dotlist form (`agents.heartbeat=[]`), which bypasses `_preprocess`.

Both verified by running pristine `upstream-base` in a worktree and counting firings
over 12 simulated evals.

**There is a config-only way to run Condition B on stock CORAL**, and it is worth
knowing: name all four actions with an unreachable interval
(`every: 1000000`; plateau uses `streak >= every`, interval uses `count % every == 0`,
and `every` has no upper bound). Naming all four defeats *both* regrowth paths. Do not
use `every: 0` — `count % 0` raises `ZeroDivisionError`. Pinned by
`test_unreachable_every_disables_heartbeats_without_any_code_change`.

We instead fixed both regrowth paths on the fork branch `task3-ablation`, so
`heartbeat: []` means what it says. That is a **defect fix, not a prerequisite** for
the arm — say so in the write-up rather than claiming B was impossible without code.

**Condition A genuinely does need a code change.** There is no working switch.
`SharingConfig` (`sharing.notes` / `.skills` / `.attempts`) looks like one but is dead
config — nothing in the upstream tree ever reads it. Implemented on the fork as
`agents.knowledge: bool = True`; see `task3/README.md` for semantics and confounds.

**Reuse the existing Task 2 run** (`task2/results/job-shop-scheduling/2026-07-09_235518/`)
as one "full CORAL" sample; it is preserved. ~2 h per run, so 9 runs ≈ 18 h.

**Then Task 4** (improve knowledge accumulation) must modify CORAL's source — a prompt or
hyperparameter change explicitly does not qualify. `coral-upstream/` is currently a plain
clone pointed at upstream and **gitignored**; convert it to a fork/submodule *before*
editing, or the diff Task 4 is graded on will not exist in the submission.

---

## 8. Reporting

The user wants the **final report as HTML** (published via the Artifact tool), not
markdown. Per-task working notes stay as markdown (`task1/REPORT.md`, `task2/REPORT.md`);
the top-level Tasks 1–6 deliverable should be an Artifact. Load the `artifact-design`
skill first, keep the file path stable across redeploys so the URL doesn't change.

Task 5 (product plan) and Task 6 (extras) are written, not experimental. Task 6 has ready
material: the four CORAL defects above.
