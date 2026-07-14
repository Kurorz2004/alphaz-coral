"""Generate the PUBLIC training instances (visible to the agent).

Same generator and same shapes as the hidden test set, different seeds. The agent
develops against these; it is scored on the hidden set. Lower bounds are exact,
so the agent can compute its own score locally with the grader's formula.

    uv run --with numpy python tools/make_train_instances.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from make_hidden_instances import lower_bound, taillard, write_instance

OUT = Path(__file__).resolve().parent.parent / "seed" / "instances"

# Distinct seeds from the hidden set (which uses 20001-3, 50001-3, 100001-3).
SPEC = [
    ("train_020x020_a", 20, 20, 21001),
    ("train_020x020_b", 20, 20, 21002),
    ("train_050x050_a", 50, 50, 51001),
    ("train_050x050_b", 50, 50, 51002),
    ("train_100x100_a", 100, 100, 101001),
    ("train_100x100_b", 100, 100, 101002),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reference: dict[str, dict] = {}

    for name, n_jobs, n_machines, seed in SPEC:
        machines, durations = taillard(n_jobs, n_machines, seed)
        lb, lb_job, lb_machine = lower_bound(machines, durations)
        write_instance(OUT / f"{name}.jss", machines, durations)
        reference[name] = {
            "lower_bound": lb,
            "lb_job": lb_job,
            "lb_machine": lb_machine,
            "jobs": n_jobs,
            "machines": n_machines,
            "operations": n_jobs * n_machines,
            "generator_seed": seed,
        }
        print(f"  {name:<17} {n_jobs:>3}x{n_machines:<3} ops={n_jobs * n_machines:>6}  LB={lb:>6}")

    (OUT / "reference.json").write_text(json.dumps(reference, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {len(reference)} training instances -> {OUT}")


if __name__ == "__main__":
    main()
