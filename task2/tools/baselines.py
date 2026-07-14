"""Reference baselines on the hidden JSSP test set.

Classical priority dispatching rules, scored with the same formula the grader
uses (mean of optimum / makespan). These are the "known baseline" that Task 2's
improvement is measured against, alongside the naive seed.

    uv run python tools/baselines.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "seed"))

from evaluate_local import load, validate  # noqa: E402


def dispatch(machines, durations, priority) -> list[list[int]]:
    """Non-delay list scheduling under a priority rule.

    At each step, consider every job's next operation, take the earliest possible
    start time, and among the operations that can start at that time pick the one
    the rule ranks best (lowest key).
    """
    n_jobs, n_machines = len(machines), len(machines[0])
    starts = [[0] * n_machines for _ in range(n_jobs)]
    machine_free = [0] * n_machines
    job_ready = [0] * n_jobs
    next_op = [0] * n_jobs
    remaining = n_jobs * n_machines

    while remaining:
        candidates = []
        for j in range(n_jobs):
            k = next_op[j]
            if k >= n_machines:
                continue
            start = max(job_ready[j], machine_free[machines[j][k]])
            candidates.append((start, j, k))

        earliest = min(c[0] for c in candidates)
        ready = [c for c in candidates if c[0] == earliest]
        _, j, k = min(ready, key=lambda c: (priority(c[1], c[2], durations, n_machines), c[1]))

        starts[j][k] = earliest
        machine_free[machines[j][k]] = earliest + durations[j][k]
        job_ready[j] = earliest + durations[j][k]
        next_op[j] += 1
        remaining -= 1

    return starts


RULES = {
    "FIFO (seed rule)": lambda j, k, d, nm: 0,
    "SPT  (shortest processing time)": lambda j, k, d, nm: d[j][k],
    "LPT  (longest processing time)": lambda j, k, d, nm: -d[j][k],
    "MWKR (most work remaining)": lambda j, k, d, nm: -sum(d[j][k:]),
    "LWKR (least work remaining)": lambda j, k, d, nm: sum(d[j][k:]),
}


def main() -> None:
    reference = json.loads((ROOT / "taskdata" / "reference.json").read_text())
    names = sorted(reference)
    loaded = {n: load(ROOT / "taskdata" / "instances" / f"{n}.jss") for n in names}

    print(f"{'rule':<34} {'score':>9} {'mean gap vs LB':>16}")
    print("-" * 61)
    for label, rule in RULES.items():
        ratios, gaps = [], []
        for name in names:
            _, _, machines, durations = loaded[name]
            starts = dispatch(machines, durations, rule)
            makespan = validate(machines, durations, starts)
            bound = reference[name]["lower_bound"]
            ratios.append(bound / makespan)
            gaps.append(100 * (makespan - bound) / bound)
        print(f"{label:<34} {sum(ratios) / len(ratios):>9.6f} {sum(gaps) / len(gaps):>15.2f}%")

    # Tabu reference (vendored agent solver), for context only.
    if all("best_known" in reference[n] for n in names):
        ratios = [reference[n]["lower_bound"] / reference[n]["best_known"] for n in names]
        gaps = [reference[n]["best_known_gap_pct"] for n in names]
        print(f"{'tabu reference (20s/instance)':<34} {sum(ratios) / len(ratios):>9.6f} {sum(gaps) / len(gaps):>15.2f}%")

    print("-" * 61)
    print(f"{'lower bound (unattainable)':<34} {1.0:>9.6f} {0.0:>15.2f}%")


if __name__ == "__main__":
    main()
