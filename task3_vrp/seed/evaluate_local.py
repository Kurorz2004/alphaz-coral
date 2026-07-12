"""Score solution.py on the PUBLIC development instances.

The official score comes from `coral eval`, which grades on a *hidden* instance
set you cannot see. This harness applies the same feasibility rules and the
same scoring formula to the visible instances in `instances/`.

Score = mean of `reference_distance / solver_distance`. Higher is strictly
better; a score of 1.0 means you matched the reference. The reference is a
strong-heuristic solution (not a proven optimum), so the score can slightly
exceed 1.0 if the solver beats it.

Usage:
    python evaluate_local.py
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

from solution import solve

HERE = Path(__file__).parent
TIME_LIMIT = 10.0
BASE_SEED = 12345


def _load_vrp(path: Path) -> dict:
    """Parse a CVRPLIB-format .vrp file."""
    data = {
        "name": "", "dimension": 0, "capacity": 0,
        "node_coords": {}, "demands": {},
    }
    section = None
    for raw in path.read_text().splitlines():
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


def _validate(
    routes: list[list[int]], dimension: int,
    capacity: int, demands: list[int], n_vehicles: int,
) -> int:
    """Return total distance, or raise ValueError on first violation."""
    if len(routes) > n_vehicles:
        raise ValueError(
            f"used {len(routes)} routes but only {n_vehicles} vehicles available"
        )

    visited = [0] * dimension
    for ri, route in enumerate(routes):
        load = 0
        for c in route:
            if c < 1 or c >= dimension:
                raise ValueError(
                    f"route {ri}: customer index {c} out of range [1, {dimension})"
                )
            visited[c] += 1
            load += demands[c]
        if load > capacity:
            raise ValueError(
                f"route {ri}: demand {load} exceeds capacity {capacity}"
            )

    for c in range(1, dimension):
        if visited[c] == 0:
            raise ValueError(f"customer {c} was not visited")
        if visited[c] > 1:
            raise ValueError(f"customer {c} visited {visited[c]} times")


def _compute_distance(
    routes: list[list[int]], coords: list[tuple[int, int]],
) -> int:
    """Compute total EUC_2D distance."""
    def _d(i: int, j: int) -> int:
        dx = coords[i][0] - coords[j][0]
        dy = coords[i][1] - coords[j][1]
        return int(math.sqrt(dx * dx + dy * dy) + 0.5)

    total = 0
    for route in routes:
        prev = 0
        for c in route:
            total += _d(prev, c)
            prev = c
        total += _d(prev, 0)
    return total


def main() -> None:
    instances_dir = HERE / "instances"
    ref_path = instances_dir / "reference.json"
    if not ref_path.exists():
        print("No reference.json found — the dev instances are missing. Report this.")
        return

    reference = json.loads(ref_path.read_text())
    scores, rows = [], []

    for index, name in enumerate(sorted(reference)):
        inst_path = instances_dir / f"{name}.vrp"
        if not inst_path.exists():
            print(f"SKIP {name}: instance file not found")
            continue

        vrp = _load_vrp(inst_path)
        dimension = int(vrp["dimension"])
        capacity = int(vrp["capacity"])
        node_coords = [vrp["node_coords"][i + 1] for i in range(dimension)]
        demands = [vrp["demands"].get(i + 1, 0) for i in range(dimension)]
        import re
        m = re.search(r"-k(\d+)", vrp.get("name", ""))
        n_vehicles = int(m.group(1)) if m else dimension - 1

        meta = reference[name]
        ref = meta["bks_distance"]

        started = time.time()
        routes = solve(
            dimension, capacity, node_coords, demands,
            n_vehicles, TIME_LIMIT, BASE_SEED + index,
        )
        elapsed = time.time() - started

        _validate(routes, dimension, capacity, demands, n_vehicles)
        dist = _compute_distance(routes, node_coords)
        score = ref / dist if dist > 0 else 0.0
        gap = 100.0 * (dist - ref) / ref
        scores.append(score)
        rows.append((name, meta["n_customers"], ref, dist, gap, len(routes), elapsed))

    if not rows:
        print("No instances to evaluate.")
        return

    print(
        f"{'instance':<20} {'n':>5} {'ref':>8} {'dist':>8} {'gap':>8} "
        f"{'routes':>7} {'score':>9} {'sec':>7}"
    )
    for name, n_cust, ref, dist, gap, nr, elapsed in rows:
        score = ref / dist if dist > 0 else 0.0
        print(
            f"{name:<20} {n_cust:>5} {ref:>8} {dist:>8} {gap:>+7.2f}% "
            f"{nr:>7} {score:>9.6f} {elapsed:>6.2f}"
        )

    final_score = sum(scores) / len(scores)
    mean_gap = sum(r[4] for r in rows) / len(rows)
    print(f"\nScore (mean ref/dist) = {final_score:.6f}")
    print(f"Mean gap               = {mean_gap:+.2f}%")


if __name__ == "__main__":
    main()
