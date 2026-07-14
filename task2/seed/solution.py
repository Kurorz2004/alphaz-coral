"""Baseline job-shop scheduler: greedy non-delay list scheduling.

Operations are dispatched in order of job index. Whenever a machine falls idle,
the lowest-indexed job with a ready operation on that machine is scheduled.
This is a valid, deterministic schedule -- and a mediocre one.

Must define:

    solve(machines, durations, time_limit, seed) -> starts

  machines[j][k]  machine running the k-th operation of job j
  durations[j][k] its processing time
  starts[j][k]    integer start time you assign

Feasibility (enforced by the grader, violations score nothing):
  * starts[j][k] >= starts[j][k-1] + durations[j][k-1]   (job precedence)
  * operations on the same machine never overlap          (machine disjunction)
"""

from __future__ import annotations


def solve(
    machines: list[list[int]],
    durations: list[list[int]],
    time_limit: float,
    seed: int,
) -> list[list[int]]:
    """Schedule every operation as early as possible, breaking ties by job index."""
    n_jobs = len(machines)
    n_machines = len(machines[0])

    starts = [[0] * n_machines for _ in range(n_jobs)]

    machine_free_at = [0] * n_machines  # when each machine next becomes idle
    job_ready_at = [0] * n_jobs  # when each job's next operation may begin
    next_op = [0] * n_jobs  # index of each job's next unscheduled operation
    remaining = n_jobs * n_machines

    while remaining:
        # Among all jobs with an unscheduled operation, pick the one that can
        # start earliest; ties go to the lowest job index. This is a pure
        # priority rule -- no lookahead, no backtracking, no randomisation.
        best_job = -1
        best_start = None

        for j in range(n_jobs):
            k = next_op[j]
            if k >= n_machines:
                continue
            start = max(job_ready_at[j], machine_free_at[machines[j][k]])
            if best_start is None or start < best_start:
                best_start, best_job = start, j

        j = best_job
        k = next_op[j]
        machine = machines[j][k]
        duration = durations[j][k]

        starts[j][k] = best_start
        machine_free_at[machine] = best_start + duration
        job_ready_at[j] = best_start + duration
        next_op[j] += 1
        remaining -= 1

    return starts
