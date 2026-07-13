"""Shared helpers: grader-identical distance, .vrp/.sol parsing, HGS runner."""
from __future__ import annotations

import math
import os

DATA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST_DIR = os.path.join(DATA, "xml100", "instances")
SOL_DIR = os.path.join(DATA, "xml100", "solutions")


def load_vrp(path):
    """Parse a .vrp exactly the way the grader's child process does."""
    data = {"name": "", "dimension": 0, "capacity": 0, "node_coords": {}, "demands": {}}
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
            p = line.split()
            data["node_coords"][int(p[0])] = (int(p[1]), int(p[2]))
        elif section == "demands":
            p = line.split()
            data["demands"][int(p[0])] = int(p[1])
    dim = data["dimension"]
    coords = [data["node_coords"][i + 1] for i in range(dim)]
    demands = [data["demands"].get(i + 1, 0) for i in range(dim)]
    return dim, data["capacity"], coords, demands


def grader_dist(coords, i, j):
    """THE grader's _dist, verbatim."""
    dx = coords[i][0] - coords[j][0]
    dy = coords[i][1] - coords[j][1]
    return int(math.sqrt(dx * dx + dy * dy) + 0.5)


def grader_cost(coords, routes):
    """Total cost of routes (customer indices, depot 0 implied) per the grader."""
    total = 0
    for route in routes:
        prev = 0
        for c in route:
            total += grader_dist(coords, prev, c)
            prev = c
        total += grader_dist(coords, prev, 0)
    return total


def load_sol(path):
    """Return (routes, cost_from_file). .sol last line is 'Cost NNNNN' (no colon)."""
    routes, cost = [], None
    for raw in open(path):
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith("route"):
            routes.append([int(x) for x in line.split(":", 1)[1].split()])
        elif line.lower().startswith("cost"):
            cost = int(line.split()[-1])
    return routes, cost


def solve_hgs(vrp_path, seconds, seed=42, num_vehicles=None):
    """Run PyVRP HGS. Returns (cost, routes_as_customer_lists, n_routes, feasible).

    round_func='round' -> distances are np.round(euclidean) on int coords.
    num_vehicles=None keeps the file default (dimension-1 = 100, i.e. free fleet).
    """
    from pyvrp import Model, read, solve
    from pyvrp.stop import MaxRuntime

    data = read(vrp_path, round_func="round")
    if num_vehicles is not None:
        vt = data.vehicle_type(0)
        data = data.replace(vehicle_types=[vt.replace(num_available=num_vehicles)])
    res = solve(data, stop=MaxRuntime(seconds), seed=seed, display=False)
    routes = [list(r.visits()) for r in res.best.routes()]
    feas = res.is_feasible()
    # res.cost() is math.inf when the best solution is infeasible -> int() would
    # raise OverflowError. Report None instead so the caller can record the miss.
    cost = int(res.cost()) if feas else None
    return cost, routes, len(routes), feas
