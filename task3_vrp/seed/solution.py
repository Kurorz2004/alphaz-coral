"""CVRP solver.

Must define:

    solve(dimension, capacity, node_coords, demands, n_vehicles, time_limit, seed)
        -> routes

where `routes` is a list of lists of customer indices (1-indexed, depot excluded).
"""

from __future__ import annotations

import math


def _build_dm(coords: list[tuple[int, int]]) -> list[list[int]]:
    n = len(coords)
    dm = [[0] * n for _ in range(n)]
    for i in range(n):
        xi, yi = coords[i]
        for j in range(i + 1, n):
            dx = xi - coords[j][0]
            dy = yi - coords[j][1]
            d = int(math.sqrt(dx * dx + dy * dy) + 0.5)
            dm[i][j] = d
            dm[j][i] = d
    return dm


def solve(
    dimension: int,
    capacity: int,
    node_coords: list[tuple[int, int]],
    demands: list[int],
    n_vehicles: int,
    time_limit: float,
    seed: int,
) -> list[list[int]]:
    """Solve the CVRP instance.

    Args:
        dimension: total nodes (1 depot + N customers)
        capacity: vehicle capacity
        node_coords: list of (x, y) for each node, index 0 = depot
        demands: list of demand for each node, demands[0] = 0
        n_vehicles: number of vehicles available
        time_limit: seconds allowed
        seed: random seed

    Returns:
        list[list[int]]: routes, each route is a list of customer indices (1..dimension-1)
    """
    dm = _build_dm(node_coords)

    remaining = set(range(1, dimension))
    routes: list[list[int]] = []

    while remaining:
        route: list[int] = []
        load = 0
        at = 0
        while True:
            candidates = [c for c in remaining if load + demands[c] <= capacity]
            if not candidates:
                if not route:
                    # Nothing fits here; take whatever is left so the outer
                    # loop keeps making progress, then close this route.
                    next_node = min(remaining, key=lambda c: (demands[c], c))
                    route.append(next_node)
                    load += demands[next_node]
                    at = next_node
                    remaining.discard(next_node)
                break
            next_node = min(
                candidates, key=lambda c: (dm[at][c], c)
            )
            route.append(next_node)
            load += demands[next_node]
            at = next_node
            remaining.discard(next_node)
            if not remaining:
                break
        routes.append(route)

    if len(routes) > n_vehicles:
        raise ValueError(
            f"{len(routes)} routes required but only {n_vehicles} vehicles available"
        )

    return routes
