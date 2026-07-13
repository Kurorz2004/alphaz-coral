# Alpha Z Technical Assessment — CORAL

Working repository for the Alpha Z technical assessment built around
[CORAL](https://github.com/Human-Agent-Society/CORAL) (arXiv 2604.01658).
Task specification: [`TE M2-1.pdf`](./TE%20M2-1.pdf).

> **Picking this up fresh?** Read [`HANDOFF.md`](./HANDOFF.md) first — it covers the
> required `core.autocrlf` fix (without which `coral start` dies with no logs), what
> Tasks 1–2 established, the four CORAL defects found, and the design traps to avoid.

## Tasks

1. **Replicate** — Deploy CORAL, run ≥1 example from `examples/`, report Final Score,
   #Evals, and a comparison table vs. the paper.
2. **OR problem** — Write `grader.py` + seed + `task.yaml` for a combinatorial
   optimization problem; report improvement over the naive seed / a known baseline.
3. **Ablation** — (A) disable notes/skills, (B) disable heartbeats; ≥3 runs each,
   report mean ± std of Final Score.
4. **Improve CORAL** — Non-trivial code change to knowledge accumulation
   (distillation / memory mgmt); comparative ≥3 runs each vs. vanilla.
5. **Product plan** — LLM-driven autonomous optimization tool (written).
6. **Extras** — Anything else.

## Repository layout

| Path | Purpose |
|------|---------|
| `coral-upstream/` | Cloned CORAL (gitignored for now → fork/submodule for Task 4). |
| `task1/` | Replication run + report. |
| _(added as tasks progress)_ | |

## Environment

- Windows 11 + WSL2 (all runs execute under WSL). `uv`, `git`, `claude` (Claude Code), `tmux`.
- **No Docker, no OpenCode, no Node.js under Linux** → `preset: docker-opencode` tasks
  cannot run as-is; use `preset: local-claude`.
- CORAL installed as an **editable** clone (`uv sync` in `coral-upstream/`) so Task 4 can modify its source.

### Required setup gotcha

`coral-upstream/` was cloned by Git for Windows (CRLF). Under WSL git this makes every
tracked file read as modified, so `hatch-vcs`'s `git describe --dirty` exceeds
setuptools-scm's 40 s timeout and `coral start` dies **with no logs**. Fix once:

```bash
git -C coral-upstream config core.autocrlf input
```

See [`task1/REPORT.md`](task1/REPORT.md) § *Defects found in CORAL* for this and two others.

## Status

- [x] **Task 1** — replication ([`task1/REPORT.md`](task1/REPORT.md)) — `circle_packing`,
      single-agent Opus: sum of radii **2.635983** (score **1.000002**) in **2 evals**
      vs. the paper's 2.6360 in 11. Verified feasible at machine precision.
- [x] **Task 2** — OR problem ([`task2/REPORT.md`](task2/REPORT.md)) — job-shop scheduling on
      9 generated square instances (20×20 / 50×50 / 100×100), scored against an exact lower
      bound. Seed **0.5424** → CORAL **0.7219** (**+33.1%**), beating a classical tabu search
      given **twice** the compute budget (0.7051).
- [x] **Task 3** — ablation ([`task3_vrp/REPORT.md`](task3_vrp/REPORT.md)) — CVRP, 3×3 runs.
      Control **0.9771 ± 0.0056**, (A) notes/skills off **0.9819 ± 0.0071**, (B) heartbeats off
      **0.9803 ± 0.0012**. **Null** — both ablations scored *nominally better* (g ≈ −0.6, p = 0.70).
      The finding is the diagnosis: seed noise (0.011–0.014) is **3× the condition effect** (0.0048),
      and 46–65% of all gain lands on attempt 1 (the model *recalls* Clarke-Wright → Prins split →
      giant-tour ILS). CVRP cannot discriminate the hypothesis — a knowledge channel can only pay
      off if there is knowledge to accumulate. Dataset rebuilt from a generator first: Set X's
      optimal routes are published and `dimension` uniquely keys them, so a 5-line lookup would
      have scored ~1.0.
- [ ] Task 4 — CORAL improvement
- [ ] Task 5 — product plan
- [ ] Task 6 — extras
