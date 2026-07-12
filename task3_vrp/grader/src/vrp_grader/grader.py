"""Capacitated Vehicle Routing Problem (CVRP) grader.

The agent's program must define::

    solve(dimension, capacity, node_coords, demands, n_vehicles, time_limit, seed)
        -> list[list[int]]

where each inner list is a vehicle route (customer indices only — depot 0 is
implied at both ends). The total demand on any route must not exceed capacity,
every customer must be visited exactly once, and at most n_vehicles routes may
be used.

Score = mean over hidden instances of `best_known_distance / solver_distance`.

Distances are EUC_2D per the CVRPLIB convention: double-precision Euclidean
rounded to the nearest integer.

Any infeasible or malformed solution fails the entire evaluation.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from coral.grader import TaskGrader
from coral.types import ScoreBundle


class Grader(TaskGrader):
    """Grader for CVRP on a hidden instance set drawn from CVRPLIB Set X."""

    def get_python_command(self) -> list[str]:
        """Pin execution to the grader venv.

        The default implementation switches to ``uv run --project <codebase>``
        when the agent's repo contains a pyproject.toml, which would let the
        agent add an exact solver (ortools) and trivially win. Pinned to
        sys.executable so only the grader's declared deps are available.
        """
        return [sys.executable]

    def evaluate(self) -> ScoreBundle:
        program_file = self.args.get("program_file", "solution.py")
        time_limit = float(self.args.get("time_limit", 10.0))
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
            instance_path = taskdata / "instances" / f"{name}.vrp"
            if not instance_path.exists():
                return self.fail(f"Hidden instance missing: {name}")

            meta = reference[name]
            bks_distance = meta["bks_distance"]

            try:
                result = _run_one(
                    program_path=program_path,
                    instance_path=instance_path,
                    time_limit=time_limit,
                    seed=base_seed + index,
                    bks_distance=bks_distance,
                    python_cmd=self.get_python_command(),
                    wall_timeout=time_limit * 3.0 + 60.0,
                )
            except subprocess.TimeoutExpired:
                return self.fail(
                    f"{name}: solve() exceeded the wall clock budget "
                    f"({time_limit}s advertised)"
                )
            except Exception as exc:  # noqa: BLE001
                return self.fail(f"{name}: evaluation failed: {exc}")

            if "error" in result:
                return self.fail(f"{name}: {result['error']}")

            solver_dist = int(result["total_distance"])
            score = bks_distance / solver_dist if solver_dist > 0 else 0.0
            gap_pct = 100.0 * (solver_dist - bks_distance) / bks_distance

            results.append(
                {
                    "name": name,
                    "bks_distance": bks_distance,
                    "solver_distance": solver_dist,
                    "score": score,
                    "gap_pct": gap_pct,
                    "n_routes": result["n_routes"],
                    "seconds": result.get("seconds", 0.0),
                }
            )

        final_score = sum(r["score"] for r in results) / len(results)
        mean_gap = sum(r["gap_pct"] for r in results) / len(results)
        worst = max(results, key=lambda r: r["gap_pct"])
        best = min(results, key=lambda r: r["gap_pct"])
        total_seconds = sum(r["seconds"] for r in results)

        detail = " | ".join(
            f"{r['name']}={r['solver_distance']}({r['gap_pct']:+.1f}%)"
            for r in results
        )
        explanation = (
            f"Score: {final_score:.6f} | mean gap: {mean_gap:+.2f}% | "
            f"best gap: {best['gap_pct']:+.2f}% ({best['name']}) | "
            f"worst gap: {worst['gap_pct']:+.2f}% ({worst['name']}) | "
            f"solved {len(results)} instances in {total_seconds:.1f}s\n{detail}"
        )

        return self.score(final_score, explanation)


_CHILD = textwrap.dedent(
    """\
import json, sys, time, importlib.util, random, math

program_path, instance_path, time_limit, seed = (
    sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]),
)

# --- load instance ----------------------------------------------------------
def _load_vrp(path: str) -> dict:
    \"\"\"Parse a CVRPLIB-format .vrp file. Returns instance dict.\"\"\"
    data = {
        "name": "", "dimension": 0, "capacity": 0,
        "node_coords": {}, "demands": {},
    }
    section = None
    for raw in open(path):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "NODE_COORD_SECTION":
            section = "coords"
        elif line == "DEMAND_SECTION":
            section = "demands"
        elif line == "DEPOT_SECTION":
            section = "depot"
        elif line == "EOF":
            break
        elif ":" in line and section is None:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            if key == "DIMENSION":
                data["dimension"] = int(val.split()[0])
            elif key == "CAPACITY":
                data["capacity"] = int(val.split()[0])
            elif key == "NAME":
                data["name"] = val
        elif section == "coords":
            parts = line.split()
            node = int(parts[0])
            data["node_coords"][node] = (int(parts[1]), int(parts[2]))
        elif section == "demands":
            parts = line.split()
            node = int(parts[0])
            data["demands"][node] = int(parts[1])
    return data

vrp = _load_vrp(instance_path)
dimension = vrp["dimension"]
capacity = vrp["capacity"]

# Build ordered arrays (1-indexed -> 0-indexed)
node_coords = [vrp["node_coords"][i + 1] for i in range(dimension)]
demands = [vrp["demands"].get(i + 1, 0) for i in range(dimension)]

# n_vehicles from instance name (e.g. X-n101-k25 -> 25)
import re as _re
m = _re.search(r"-k(\\d+)", vrp.get("name", ""))
n_vehicles = int(m.group(1)) if m else dimension - 1

# --- import solver ----------------------------------------------------------
spec = importlib.util.spec_from_file_location("solution", program_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

random.seed(seed)
started = time.time()
try:
    routes = module.solve(
        dimension, capacity, node_coords, demands,
        n_vehicles, time_limit, seed,
    )
except Exception as exc:
    print(json.dumps({"error": f"solve() raised: {type(exc).__name__}: {exc}"}))
    sys.exit(0)
seconds = time.time() - started

# --- structural validation --------------------------------------------------
if not isinstance(routes, list):
    print(json.dumps({"error": "solve() must return a list of routes"}))
    sys.exit(0)
if not all(isinstance(r, list) for r in routes):
    print(json.dumps({"error": "each route must be a list of customer indices"}))
    sys.exit(0)
if not all(isinstance(c, int) for r in routes for c in r):
    print(json.dumps({"error": "route entries must be integers (customer indices)"}))
    sys.exit(0)

if len(routes) > n_vehicles:
    print(json.dumps({
        "error": f"used {len(routes)} routes but only {n_vehicles} vehicles available"
    }))
    sys.exit(0)

# --- check every customer visited exactly once --------------------------------
visited = [0] * dimension
for ri, route in enumerate(routes):
    for c in route:
        if c < 1 or c >= dimension:
            print(json.dumps({
                "error": (
                    f"route {ri}: customer index {c} out of range "
                    f"[1, {dimension})"
                )
            }))
            sys.exit(0)
        visited[c] += 1

for c in range(1, dimension):
    if visited[c] == 0:
        print(json.dumps({"error": f"customer {c} was not visited"}))
        sys.exit(0)
    if visited[c] > 1:
        print(json.dumps({"error": f"customer {c} visited {visited[c]} times"}))
        sys.exit(0)

# --- compute EUC_2D distance matrix ------------------------------------------
def _dist(i: int, j: int) -> int:
    dx = node_coords[i][0] - node_coords[j][0]
    dy = node_coords[i][1] - node_coords[j][1]
    return int(math.sqrt(dx * dx + dy * dy) + 0.5)

total_distance = 0
for ri, route in enumerate(routes):
    route_demand = 0
    prev = 0  # depot
    for c in route:
        route_demand += demands[c]
        total_distance += _dist(prev, c)
        prev = c
    total_distance += _dist(prev, 0)  # back to depot
    if route_demand > capacity:
        print(json.dumps({
            "error": (
                f"route {ri}: demand {route_demand} exceeds "
                f"capacity {capacity}"
            )
        }))
        sys.exit(0)

print(json.dumps({
    "total_distance": total_distance,
    "n_routes": len(routes),
    "seconds": seconds,
}))
"""
)


def _run_one(
    *,
    program_path: str,
    instance_path: Path,
    time_limit: float,
    seed: int,
    bks_distance: int,
    python_cmd: list[str],
    wall_timeout: float,
) -> dict:
    """Run and validate the agent's solver on a single instance, in isolation."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"

    completed = subprocess.run(
        [
            *python_cmd,
            "-c",
            _CHILD,
            program_path,
            str(instance_path),
            str(time_limit),
            str(seed),
        ],
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
