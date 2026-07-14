"""Job-Shop Scheduling (JSSP) grader.

The agent's program must define:

    solve(machines, durations, time_limit, seed) -> starts

where ``machines[j][k]`` is the machine that runs the k-th operation of job j,
``durations[j][k]`` its processing time, and ``starts[j][k]`` the integer start
time the solver assigns. A schedule is feasible iff

    1. precedence : starts[j][k] >= starts[j][k-1] + durations[j][k-1]
    2. disjunction: operations sharing a machine never overlap
    3. starts are non-negative integers

Score = mean over the hidden instances of ``lower_bound / makespan``. The bound is
``max(busiest machine load, longest job chain)`` — exact, instantly computable, and
provably unbeatable, so the score lies strictly in (0, 1]. At these sizes (up to
10,000 operations) no exact optimum is obtainable, and the bound is not tight, so
even an optimal schedule scores below 1.0. Higher is better; only relative
comparisons are meaningful.

Any infeasible or malformed schedule fails the whole evaluation — feasibility is
not tradeable for score.

Two deliberate anti-gaming measures:

  * The hidden instances are *generated* (Taillard scheme), not public benchmarks,
    so no memorized schedule can be looked up.
  * ``get_python_command`` is pinned to the grader venv, so the agent's program
    runs with exactly the dependencies declared here. There is no CP-SAT / MILP
    solver available: the agent must write a heuristic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from coral.grader import TaskGrader
from coral.types import ScoreBundle


class Grader(TaskGrader):
    """Grader for job-shop scheduling on a hidden, generated instance set."""

    def get_python_command(self) -> list[str]:
        """Pin execution to the grader venv.

        The default implementation switches to ``uv run --project <codebase>``
        when the agent's repo contains a pyproject.toml, which would let the
        agent add an exact solver (ortools) and trivially win. Pinning to
        sys.executable fixes the dependency surface to this package's deps.
        """
        return [sys.executable]

    def evaluate(self) -> ScoreBundle:
        program_file = self.args.get("program_file", "solution.py")
        time_limit = float(self.args.get("time_limit", 15.0))
        base_seed = int(self.args.get("base_seed", 12345))

        program_path = os.path.join(self.codebase_path, program_file)
        if not os.path.exists(program_path):
            return self.fail(f"Program file not found: {program_file}")

        taskdata = Path(self.private_dir) / "taskdata"
        reference_path = taskdata / "reference.json"
        if not reference_path.exists():
            return self.fail("Hidden reference.json not found")
        reference = json.loads(reference_path.read_text())

        instances = sorted(reference)
        results: list[dict] = []

        for index, name in enumerate(instances):
            instance_path = taskdata / "instances" / f"{name}.jss"
            if not instance_path.exists():
                return self.fail(f"Hidden instance missing: {name}")

            try:
                result = _run_one(
                    program_path=program_path,
                    instance_path=instance_path,
                    time_limit=time_limit,
                    seed=base_seed + index,
                    python_cmd=self.get_python_command(),
                    # Generous slack over the advertised per-instance budget: a
                    # 100x100 instance has 10,000 operations, so even reading and
                    # constructing an initial schedule costs real time.
                    wall_timeout=time_limit * 3.0 + 60.0,
                )
            except subprocess.TimeoutExpired:
                return self.fail(f"{name}: solve() exceeded the wall clock budget ({time_limit}s advertised)")
            except Exception as exc:  # noqa: BLE001 - surface any harness failure verbatim
                return self.fail(f"{name}: evaluation failed: {exc}")

            if "error" in result:
                return self.fail(f"{name}: {result['error']}")

            bound = int(reference[name]["lower_bound"])
            makespan = int(result["makespan"])
            if makespan < bound:
                return self.fail(
                    f"{name}: makespan {makespan} is below the lower bound {bound} — "
                    "schedule validation is wrong or the instance was mutated"
                )

            results.append(
                {
                    "name": name,
                    "makespan": makespan,
                    "bound": bound,
                    "ratio": bound / makespan,
                    "gap_pct": 100.0 * (makespan - bound) / bound,
                    "seconds": result.get("seconds", 0.0),
                }
            )

        score = sum(r["ratio"] for r in results) / len(results)
        mean_gap = sum(r["gap_pct"] for r in results) / len(results)
        worst = max(results, key=lambda r: r["gap_pct"])
        total_seconds = sum(r["seconds"] for r in results)

        detail = " | ".join(f"{r['name']}={r['makespan']}({r['gap_pct']:+.1f}%)" for r in results)
        explanation = (
            f"Score: {score:.6f} | mean gap over lower bound: {mean_gap:.2f}% | "
            f"worst: {worst['name']} {worst['gap_pct']:+.1f}% | "
            f"solved {len(results)} instances in {total_seconds:.1f}s\n{detail}"
        )

        return self.score(score, explanation)


_CHILD = textwrap.dedent(
    """\
    import json, sys, time, importlib.util, random

    program_path, instance_path, time_limit, seed = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])

    def load(path):
        rows = [ln for ln in open(path).read().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
        n_jobs, n_machines = map(int, rows[0].split())
        machines, durations = [], []
        for line in rows[1:1 + n_jobs]:
            nums = list(map(int, line.split()))
            machines.append(nums[0::2])
            durations.append(nums[1::2])
        return n_jobs, n_machines, machines, durations

    n_jobs, n_machines, machines, durations = load(instance_path)

    spec = importlib.util.spec_from_file_location("solution", program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    random.seed(seed)
    started = time.time()
    try:
        starts = module.solve(machines, durations, time_limit, seed)
    except Exception as exc:
        print(json.dumps({"error": f"solve() raised: {type(exc).__name__}: {exc}"}))
        sys.exit(0)
    seconds = time.time() - started

    # --- structural validation -------------------------------------------------
    try:
        starts = [[int(v) for v in row] for row in starts]
    except Exception:
        print(json.dumps({"error": "solve() must return a 2-D array of integer start times"}))
        sys.exit(0)
    if len(starts) != n_jobs or any(len(r) != n_machines for r in starts):
        print(json.dumps({"error": f"starts must have shape ({n_jobs}, {n_machines})"}))
        sys.exit(0)
    if any(v < 0 for row in starts for v in row):
        print(json.dumps({"error": "negative start time"}))
        sys.exit(0)

    # --- precedence: operation k+1 of a job begins only after operation k ends ---
    for j in range(n_jobs):
        for k in range(1, n_machines):
            if starts[j][k] < starts[j][k - 1] + durations[j][k - 1]:
                print(json.dumps({"error": f"precedence violated: job {j} op {k} starts at {starts[j][k]} but op {k-1} ends at {starts[j][k-1] + durations[j][k-1]}"}))
                sys.exit(0)

    # --- disjunction: no machine runs two operations at once --------------------
    by_machine = {}
    for j in range(n_jobs):
        for k in range(n_machines):
            by_machine.setdefault(machines[j][k], []).append((starts[j][k], starts[j][k] + durations[j][k], j, k))
    for m, ops in by_machine.items():
        ops.sort()
        for a, b in zip(ops, ops[1:]):
            if b[0] < a[1]:
                print(json.dumps({"error": f"machine {m} overlap: job {a[2]} op {a[3]} runs [{a[0]},{a[1]}) and job {b[2]} op {b[3]} starts at {b[0]}"}))
                sys.exit(0)

    makespan = max(starts[j][n_machines - 1] + durations[j][n_machines - 1] for j in range(n_jobs))
    print(json.dumps({"makespan": int(makespan), "seconds": seconds}))
    """
)


def _run_one(
    *,
    program_path: str,
    instance_path: Path,
    time_limit: float,
    seed: int,
    python_cmd: list[str],
    wall_timeout: float,
) -> dict:
    """Run and validate the agent's solver on a single instance, in isolation."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"  # determinism across runs

    completed = subprocess.run(
        [*python_cmd, "-c", _CHILD, program_path, str(instance_path), str(time_limit), str(seed)],
        capture_output=True,
        text=True,
        timeout=wall_timeout,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip()[-2000:])

    stdout = completed.stdout.strip()
    if not stdout:
        raise RuntimeError(f"no output; stderr: {completed.stderr.strip()[-1000:]}")
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"no valid JSON in output: {stdout[-500:]}")
