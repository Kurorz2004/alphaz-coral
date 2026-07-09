# Alpha Z Technical Assessment — CORAL

Working repository for the Alpha Z technical assessment built around
[CORAL](https://github.com/Human-Agent-Society/CORAL) (arXiv 2604.01658).
Task specification: [`TE M2-1.pdf`](./TE%20M2-1.pdf).

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

- Windows 11; `uv`, `git`, `claude` (Claude Code) available. WSL2 available as fallback.
- CORAL installed as an **editable** clone (`uv sync` in `coral-upstream/`) so Task 4 can modify its source.

## Status

- [ ] **Task 1** — replication
- [ ] Task 2 — OR problem
- [ ] Task 3 — ablation
- [ ] Task 4 — CORAL improvement
- [ ] Task 5 — product plan
- [ ] Task 6 — extras
