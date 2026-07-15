# Alpha Z Technical Assessment — CORAL

**Report (the deliverable): [`report/index.html`](./report/index.html)** — open it in a browser.
Task specification: [`TE M2-1.pdf`](./TE%20M2-1.pdf).

| Path | What is in it |
|------|---------------|
| `report/` | The final report, one self-contained HTML file and a corresponding PDF file. |
| `task1/` | Task 1: `circle_packing` replication. |
| `vrp/` | Tasks 2–4: the CVRP task (`grader/`, `seed/`, `task.yaml`) and its run/analysis scripts (`run_ablation.sh`, `run_gate.sh`, `analyze.py`). |
| `taskdata/` | The 50 hidden CVRP instances and their reference labels; `vrp/task.yaml` grades against `../taskdata`. |
| `coral-upstream/` | CORAL clone (gitignored). |
| `vrp/evidence/` | Per-run evidence: attempt store, notes/skills corpora, publication verdicts, config, and a `repo.bundle` with the full git history of each run's evolved program. |
| `coral-patches/` | The CORAL modifications (Tasks 3–4) as a patch series against upstream c535d91a; also on [the fork's `task4-llm-consolidation` branch](https://github.com/Kurorz2004/CORAL/tree/task4-llm-consolidation). |

Run results land in `vrp/results/` (gitignored).

## Reviewing the runs

```
cd vrp
uv run --project ../coral-upstream python analyze.py evidence
```

To open an evolved-program repo from a run's git bundle:

```
git clone vrp/evidence/gate/gate-s1/repo.bundle <dir>
```
