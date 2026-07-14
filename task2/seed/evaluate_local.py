"""Score solution.py on the PUBLIC training instances.

The official score comes from `coral eval`, which grades on a *hidden* instance
set you cannot see. This harness applies the same feasibility rules and the same
scoring formula to the visible instances in `instances/`, which are drawn from the
same generator and the same shapes (20x20, 50x50, 100x100) as the hidden set.

Score = mean of `lower_bound / makespan`, where the bound is
`max(busiest machine load, longest job chain)`. The bound is not tight, so even an
optimal schedule scores below 1.0. Only relative comparisons mean anything.

`benchmarks/` additionally holds classic OR-Library instances with *published
optima*, if you want to sanity-check your solver against the literature.

    python evaluate_local.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from solution import solve

HERE = Path(__file__).parent
TIME_LIMIT = 15.0
BASE_SEED = 12345


def load(path: Path) -> tuple[int, int, list[list[int]], list[list[int]]]:
    rows = [ln for ln in path.read_text().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    n_jobs, n_machines = map(int, rows[0].split())
    machines, durations = [], []
    for line in rows[1 : 1 + n_jobs]:
        nums = list(map(int, line.split()))
        machines.append(nums[0::2])
        durations.append(nums[1::2])
    return n_jobs, n_machines, machines, durations


def validate(machines, durations, starts) -> int:
    """Return the makespan, or raise ValueError describing the first violation."""
    n_jobs, n_machines = len(machines), len(machines[0])
    if len(starts) != n_jobs or any(len(r) != n_machines for r in starts):
        raise ValueError(f"starts must have shape ({n_jobs}, {n_machines})")
    if any(v < 0 for row in starts for v in row):
        raise ValueError("negative start time")

    for j in range(n_jobs):
        for k in range(1, n_machines):
            if starts[j][k] < starts[j][k - 1] + durations[j][k - 1]:
                raise ValueError(f"precedence violated: job {j} op {k}")

    by_machine: dict[int, list[tuple[int, int, int]]] = {}
    for j in range(n_jobs):
        for k in range(n_machines):
            by_machine.setdefault(machines[j][k], []).append((starts[j][k], starts[j][k] + durations[j][k], j))
    for m, ops in by_machine.items():
        ops.sort()
        for a, b in zip(ops, ops[1:]):
            if b[0] < a[1]:
                raise ValueError(f"machine {m} overlap between jobs {a[2]} and {b[2]}")

    return max(starts[j][n_machines - 1] + durations[j][n_machines - 1] for j in range(n_jobs))


def main() -> None:
    reference = json.loads((HERE / "instances" / "reference.json").read_text())
    ratios, rows = [], []

    for index, name in enumerate(sorted(reference)):
        n_jobs, n_machines, machines, durations = load(HERE / "instances" / f"{name}.jss")
        started = time.time()
        starts = solve(machines, durations, TIME_LIMIT, BASE_SEED + index)
        elapsed = time.time() - started

        makespan = validate(machines, durations, starts)
        bound = reference[name]["lower_bound"]
        ratios.append(bound / makespan)
        rows.append((name, f"{n_jobs}x{n_machines}", bound, makespan, 100 * (makespan - bound) / bound, elapsed))

    print(f"{'instance':<17} {'size':<9} {'LB':>6} {'yours':>7} {'gap vs LB':>10}  {'sec':>6}")
    for name, size, bound, makespan, gap, elapsed in rows:
        print(f"{name:<17} {size:<9} {bound:>6} {makespan:>7} {gap:>9.2f}% {elapsed:>6.2f}")

    score = sum(ratios) / len(ratios)
    mean_gap = sum(r[4] for r in rows) / len(rows)
    print(f"\nscore (mean LB/makespan) = {score:.6f}")
    print(f"mean gap over LB         = {mean_gap:.2f}%")


if __name__ == "__main__":
    main()
