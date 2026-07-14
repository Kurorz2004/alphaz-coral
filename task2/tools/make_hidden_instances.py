"""Generate the hidden JSSP test set and its exact lower bounds.

Instances use Taillard's (1993) scheme — processing times ~ U[1,99], each job's
machine order an independent uniform random permutation — at *square* shapes
(jobs == machines), which is the hard regime: the two trivial bounds

    LB_job     = longest single-job chain
    LB_machine = busiest machine's total load

are balanced, so neither is achievable and the makespan is set by conflicts
between jobs. When jobs >> machines (e.g. 200x8) LB_machine dominates by ~17x,
a plain tabu search hits it exactly, and the problem is trivial.

Sizes 20x20, 50x50 and 100x100 are far beyond exact solution: CP-SAT proves
optimality at 15x15 in seconds but cannot close 30x20 in minutes, let alone
10,000 operations. So the scoring reference is the **lower bound**, which is
exact, instantly computable, and provably unbeatable. Scores are therefore
strictly below 1.0 even for an optimal schedule.

`best_known` is recorded for the write-up only. The grader never reads it.

    uv run --with numpy python tools/make_hidden_instances.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "taskdata"

# (name, n_jobs, n_machines, seed) — fixed seeds keep the set reproducible.
SPEC = [
    ("gen_020x020_a", 20, 20, 20001),
    ("gen_020x020_b", 20, 20, 20002),
    ("gen_020x020_c", 20, 20, 20003),
    ("gen_050x050_a", 50, 50, 50001),
    ("gen_050x050_b", 50, 50, 50002),
    ("gen_050x050_c", 50, 50, 50003),
    ("gen_100x100_a", 100, 100, 100001),
    ("gen_100x100_b", 100, 100, 100002),
    ("gen_100x100_c", 100, 100, 100003),
]


def taillard(n_jobs: int, n_machines: int, seed: int):
    rng = np.random.default_rng(seed)
    durations = rng.integers(1, 100, size=(n_jobs, n_machines))
    machines = np.stack([rng.permutation(n_machines) for _ in range(n_jobs)])
    return machines, durations


def lower_bound(machines, durations) -> tuple[int, int, int]:
    """Return (LB, LB_job, LB_machine). Any feasible schedule has makespan >= LB."""
    n_jobs, n_machines = durations.shape
    lb_job = int(durations.sum(axis=1).max())
    load = np.zeros(n_machines, dtype=np.int64)
    for j in range(n_jobs):
        for k in range(n_machines):
            load[machines[j, k]] += durations[j, k]
    lb_machine = int(load.max())
    return max(lb_job, lb_machine), lb_job, lb_machine


def write_instance(path: Path, machines, durations) -> None:
    n_jobs, n_machines = durations.shape
    lines = [
        "# Generated JSSP instance (Taillard 1993: durations U[1,99], random machine order per job).",
        "# Format: '<n_jobs> <n_machines>' then one line per job of (machine duration) pairs.",
        f"{n_jobs} {n_machines}",
    ]
    for j in range(n_jobs):
        lines.append(" ".join(f"{int(machines[j, k])} {int(durations[j, k])}" for k in range(n_machines)))
    path.write_text("\n".join(lines) + "\n")


def best_known(machines, durations) -> int | None:
    """Best makespan we can find offline, for the report only. Optional."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from reference_solver import solve as reference  # noqa: PLC0415
    except Exception:
        return None
    starts = reference(machines.tolist(), durations.tolist(), 20.0, 7)
    n_jobs, n_machines = durations.shape
    return int(max(starts[j][n_machines - 1] + durations[j, n_machines - 1] for j in range(n_jobs)))


def main() -> None:
    (OUT / "instances").mkdir(parents=True, exist_ok=True)
    reference: dict[str, dict] = {}

    for name, n_jobs, n_machines, seed in SPEC:
        started = time.time()
        machines, durations = taillard(n_jobs, n_machines, seed)
        lb, lb_job, lb_machine = lower_bound(machines, durations)
        write_instance(OUT / "instances" / f"{name}.jss", machines, durations)

        entry = {
            "lower_bound": lb,
            "lb_job": lb_job,
            "lb_machine": lb_machine,
            "jobs": n_jobs,
            "machines": n_machines,
            "operations": n_jobs * n_machines,
            "generator_seed": seed,
        }
        bk = best_known(machines, durations)
        if bk is not None:
            entry["best_known"] = bk  # reporting only; the grader ignores this
            entry["best_known_gap_pct"] = round(100.0 * (bk - lb) / lb, 2)

        reference[name] = entry
        extra = f"  best_known={bk} (+{entry['best_known_gap_pct']}%)" if bk else ""
        print(
            f"  {name:<15} {n_jobs:>3}x{n_machines:<3} ops={n_jobs * n_machines:>6}  "
            f"LB={lb:>6} (job={lb_job}, mach={lb_machine}){extra}  [{time.time() - started:.1f}s]"
        )

    (OUT / "reference.json").write_text(json.dumps(reference, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {len(reference)} instances -> {OUT}")


if __name__ == "__main__":
    main()
