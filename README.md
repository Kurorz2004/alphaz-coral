# Alpha Z Technical Assessment — CORAL

Working repository for the Alpha Z technical assessment built around
[CORAL](https://github.com/Human-Agent-Society/CORAL) (arXiv 2604.01658).
Task specification: [`TE M2-1.pdf`](./TE%20M2-1.pdf).

## Final report

**[`report/index.html`](./report/index.html)** — every experimental result and observation.
Open it in a browser; it is the deliverable.

## Repository layout

| Path | Purpose |
|------|---------|
| `report/` | The final report. |
| `task1/` | Task 1: `circle_packing` replication (grader, seed, verification). |
| `task3_vrp/` | Tasks 2–4: the CVRP task itself (`grader/`, `seed/`, `task.yaml`), the ablation harness (`run_ablation.sh`), and the analysis (`analyze.py`). |
| `taskdata/` | The 50 **hidden** CVRP instances and their reference labels. `task3_vrp/task.yaml` grades against `../taskdata`, so this stays at the repo root despite the generic name. |
| `coral-upstream/` | CORAL clone (gitignored). |

The 10 public development instances are separate, in `task3_vrp/seed/instances/`, and are
disjoint from the hidden 50. Both sets are committed on purpose: the reference labels are
wall-clock bounded, so regenerating them shifts the denominator and makes conditions
incomparable.

## Running the CVRP experiments

```sh
cd task3_vrp
./run_ablation.sh                                       # all 9 runs: 3 conditions × 3 seeds
./run_ablation.sh full-s1                               # or just one run
uv run --project ../coral-upstream python analyze.py    # scores from the run results
```

The nine runs go strictly sequentially — the grader gives each solver a 10-second
*wall-clock* budget per instance, so a concurrent run would silently depress whichever
condition it shared the box with. That takes roughly 18 hours, so start it inside
tmux; it is resumable, and any run that already finished is skipped on restart.

`run_ablation.sh` expects `coral-upstream/` to be on the branch carrying the
`agents.knowledge` flag (Task 3's condition A); it checks and refuses to start otherwise.
Run results land in `task3_vrp/results/`, which is gitignored.
