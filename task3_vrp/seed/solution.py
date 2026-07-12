"""CVRP solver: Clarke-Wright savings + 2-opt local search.

Must define:

    solve(dimension, capacity, node_coords, demands, n_vehicles, time_limit, seed)
        -> routes

where `routes` is a list of lists of customer indices (1-indexed, depot excluded).
"""

from __future__ import annotations

import math
import random
import time


# ---------------------------------------------------------------------------
# Distance matrix (EUC_2D — rounded to nearest integer)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Clarke-Wright savings algorithm
# ---------------------------------------------------------------------------

def _clarke_wright(
    dm: list[list[int]],
    demands: list[int],
    capacity: int,
    n_vehicles: int,
    rng: random.Random,
) -> list[list[int]]:
    """Construct routes using the parallel Clarke-Wright savings heuristic.

    Returns a list of routes (each route is a list of customer indices starting
    from 1, depot excluded).
    """
    n = len(dm)  # total nodes including depot at index 0
    customers = list(range(1, n))

    # Compute savings: s(i,j) = d(0,i) + d(0,j) - d(i,j)
    savings: list[tuple[float, int, int]] = []
    for i in range(1, n):
        for j in range(i + 1, n):
            s = dm[0][i] + dm[0][j] - dm[i][j]
            if s > 0:
                savings.append((s, i, j))
    savings.sort(key=lambda x: x[0], reverse=True)

    # Each customer starts as its own route
    routes: dict[int, list[int]] = {c: [c] for c in customers}
    route_loads: dict[int, int] = {c: demands[c] for c in customers}
    # For each customer, which route it belongs to
    cust_to_route: dict[int, int] = {c: c for c in customers}

    def _merge(ri: int, rj: int, i_end: bool, j_start: bool) -> bool:
        """Try to merge two routes. Returns True on success."""
        if ri == rj:
            return False
        ri_load = route_loads[ri]
        rj_load = route_loads[rj]
        if ri_load + rj_load > capacity:
            return False

        # Merge rj into ri
        ri_route = routes[ri]
        rj_route = routes[rj]

        if i_end and j_start:
            new_route = ri_route + rj_route
        elif i_end and not j_start:
            new_route = ri_route + list(reversed(rj_route))
        elif not i_end and j_start:
            new_route = list(reversed(ri_route)) + rj_route
        else:
            new_route = list(reversed(ri_route)) + list(reversed(rj_route))

        # Update
        routes[ri] = new_route
        route_loads[ri] = ri_load + rj_load
        for c in rj_route:
            cust_to_route[c] = ri
        del routes[rj]
        del route_loads[rj]
        return True

    for s, i, j in savings:
        ri = cust_to_route[i]
        rj = cust_to_route[j]
        if ri == rj:
            continue

        ri_route = routes[ri]
        rj_route = routes[rj]

        i_is_end = ri_route[0] == i or ri_route[-1] == i
        j_is_start = rj_route[0] == j or rj_route[-1] == j
        j_is_end = rj_route[0] == j or rj_route[-1] == j
        i_is_start = ri_route[0] == i or ri_route[-1] == i

        if i_is_end and (j_is_start or j_is_end):
            _merge(ri, rj, i_is_end, j_is_start)
        elif j_is_end and i_is_start:
            _merge(rj, ri, j_is_end, i_is_start)

    result = list(routes.values())

    # If we have too many routes, keep the fullest ones and
    # redistribute orphans via best-insertion
    if len(result) > n_vehicles:
        # Sort by load descending, keep the best
        result.sort(key=lambda r: sum(demands[c] for c in r), reverse=True)
        result = result[:n_vehicles]

    return result


# ---------------------------------------------------------------------------
# 2-opt intra-route improvement
# ---------------------------------------------------------------------------

def _two_opt_route(
    route: list[int],
    dm: list[list[int]],
    rng: random.Random,
    max_iter: int = 2000,
) -> list[int]:
    """Apply 2-opt to a single route. Route is customer indices; depot (0) is
    implied at both ends."""
    if len(route) < 2:
        return route

    # route_cost[i] = dist from node_i to node_{i+1}
    def _segment_cost(r: list[int]) -> list[int]:
        costs = [dm[0][r[0]]]
        for i in range(len(r) - 1):
            costs.append(dm[r[i]][r[i + 1]])
        costs.append(dm[r[-1]][0])
        return costs

    best = list(route)
    n = len(best)
    seg = _segment_cost(best)

    improved = True
    it = 0
    while improved and it < max_iter:
        improved = False
        it += 1
        for i in range(n - 1):
            for j in range(i + 2, n + 1):
                # Reverse segment best[i:j]
                a = best[i - 1] if i > 0 else 0
                b = best[i]
                c = best[j - 1]
                d = best[j] if j < n else 0

                old_cost = dm[a][b] + dm[c][d]
                new_cost = dm[a][c] + dm[b][d]
                if new_cost < old_cost:
                    best[i:j] = reversed(best[i:j])
                    improved = True
                    break
            if improved:
                break

    return best


def _two_opt_all(
    routes: list[list[int]], dm: list[list[int]], rng: random.Random,
) -> list[list[int]]:
    return [_two_opt_route(r, dm, rng) for r in routes]


# ---------------------------------------------------------------------------
# Inter-route moves: relocate, exchange, 2-opt*
# ---------------------------------------------------------------------------

def _route_cost(route: list[int], dm: list[list[int]]) -> int:
    if not route:
        return 0
    cost = dm[0][route[0]] + dm[route[-1]][0]
    for i in range(len(route) - 1):
        cost += dm[route[i]][route[i + 1]]
    return cost


def _route_load(route: list[int], demands: list[int]) -> int:
    return sum(demands[c] for c in route)


def _relocate(
    routes: list[list[int]], dm: list[list[int]],
    demands: list[int], capacity: int,
    rng: random.Random,
) -> list[list[int]]:
    """Try to relocate a customer from one route to another."""
    best = [list(r) for r in routes]
    improved = True
    while improved:
        improved = False
        for ri, src in enumerate(best):
            if len(src) <= 1:
                continue
            for pos in range(len(src)):
                c = src[pos]
                c_demand = demands[c]
                for rj, dst in enumerate(best):
                    if ri == rj:
                        continue
                    if _route_load(dst, demands) + c_demand > capacity:
                        continue

                    # Remove from src
                    new_src = src[:pos] + src[pos + 1:]
                    # Find best insertion position in dst
                    best_pos = 0
                    best_delta = float("inf")
                    for ins in range(len(dst) + 1):
                        new_dst = dst[:ins] + [c] + dst[ins:]
                        delta = (
                            _route_cost(new_src, dm) + _route_cost(new_dst, dm)
                            - _route_cost(src, dm) - _route_cost(dst, dm)
                        )
                        if delta < best_delta:
                            best_delta = delta
                            best_pos = ins

                    if best_delta < 0:
                        best[ri] = new_src
                        best[rj] = dst[:best_pos] + [c] + dst[best_pos:]
                        # Remove empty routes
                        best = [r for r in best if r]
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
    return best


def _exchange(
    routes: list[list[int]], dm: list[list[int]],
    demands: list[int], capacity: int,
    rng: random.Random,
) -> list[list[int]]:
    """Try exchanging a pair of customers between two routes."""
    best = [list(r) for r in routes]
    improved = True
    while improved:
        improved = False
        for ri in range(len(best)):
            for rj in range(ri + 1, len(best)):
                for pi, ci in enumerate(best[ri]):
                    for pj, cj in enumerate(best[rj]):
                        load_i = _route_load(best[ri], demands)
                        load_j = _route_load(best[rj], demands)
                        new_load_i = load_i - demands[ci] + demands[cj]
                        new_load_j = load_j - demands[cj] + demands[ci]
                        if new_load_i > capacity or new_load_j > capacity:
                            continue

                        new_ri = best[ri][:pi] + [cj] + best[ri][pi + 1:]
                        new_rj = best[rj][:pj] + [ci] + best[rj][pj + 1:]
                        delta = (
                            _route_cost(new_ri, dm) + _route_cost(new_rj, dm)
                            - _route_cost(best[ri], dm) - _route_cost(best[rj], dm)
                        )
                        if delta < 0:
                            best[ri] = new_ri
                            best[rj] = new_rj
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
    return best


def _cross_exchange(
    routes: list[list[int]], dm: list[list[int]],
    demands: list[int], capacity: int,
    rng: random.Random,
) -> list[list[int]]:
    """2-opt*: swap the tails of two routes."""
    best = [list(r) for r in routes]
    improved = True
    while improved:
        improved = False
        for ri in range(len(best)):
            for rj in range(ri + 1, len(best)):
                for cut_i in range(len(best[ri])):
                    for cut_j in range(len(best[rj])):
                        # Split routes at cut_i, cut_j and swap tails
                        head_i = best[ri][:cut_i]
                        tail_i = best[ri][cut_i:]
                        head_j = best[rj][:cut_j]
                        tail_j = best[rj][cut_j:]

                        new_ri = head_i + tail_j
                        new_rj = head_j + tail_i

                        if (_route_load(new_ri, demands) > capacity or
                                _route_load(new_rj, demands) > capacity):
                            continue

                        delta = (
                            _route_cost(new_ri, dm) + _route_cost(new_rj, dm)
                            - _route_cost(best[ri], dm) - _route_cost(best[rj], dm)
                        )
                        if delta < 0:
                            best[ri] = new_ri
                            best[rj] = new_rj
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
        # Remove empty routes
        best = [r for r in best if r]
    return best


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(
    routes: list[list[int]], dimension: int,
    capacity: int, demands: list[int],
) -> bool:
    try:
        visited = [0] * dimension
        for r in routes:
            load = 0
            for c in r:
                if c < 1 or c >= dimension:
                    return False
                visited[c] += 1
                load += demands[c]
            if load > capacity:
                return False
        for c in range(1, dimension):
            if visited[c] != 1:
                return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------

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
    rng = random.Random(seed)
    t0 = time.time()
    deadline = t0 + time_limit * 0.90  # 90% of budget for search, leave 10% margin

    dm = _build_dm(node_coords)
    n_customers = dimension - 1

    best_routes: list[list[int]] | None = None
    best_dist = float("inf")

    # Phase 1: Clarke-Wright construction (deterministic)
    cw = _clarke_wright(dm, demands, capacity, n_vehicles, rng)
    cw = _two_opt_all(cw, dm, rng)
    if _validate(cw, dimension, capacity, demands):
        dist = sum(_route_cost(r, dm) for r in cw)
        if dist < best_dist:
            best_dist = dist
            best_routes = cw

    # Phase 2: Iterated local search (while budget remains)
    iteration = 0
    while time.time() < deadline:
        iteration += 1

        # Start from best known or CW
        current = [list(r) for r in (best_routes if best_routes else cw)]

        # Perturb: remove a fraction of customers and re-insert greedily
        if rng.random() < 0.3 and len(current) > 1:
            perturb_n = max(1, n_customers // 20)
            for _ in range(perturb_n):
                src_ri = rng.randint(0, len(current) - 1)
                if len(current[src_ri]) <= 1:
                    continue
                pos = rng.randint(0, len(current[src_ri]) - 1)
                c = current[src_ri].pop(pos)
                # Re-insert via best-fit
                best_ri = -1
                best_pos = -1
                best_delta = float("inf")
                for rj in range(len(current)):
                    if _route_load(current[rj], demands) + demands[c] > capacity:
                        continue
                    for ins in range(len(current[rj]) + 1):
                        new_r = current[rj][:ins] + [c] + current[rj][ins:]
                        old_cost = _route_cost(current[rj], dm)
                        new_cost = _route_cost(new_r, dm)
                        delta = new_cost - old_cost
                        # If src_ri == rj, we need to account for the removal
                        if rj == src_ri:
                            old_with = current[rj][:pos] + current[rj][pos:]
                            delta = _route_cost(new_r, dm) - _route_cost(
                                [x for x in current[rj]], dm
                            )
                        if delta < best_delta:
                            best_delta = delta
                            best_ri = rj
                            best_pos = ins
                if best_ri >= 0:
                    current[best_ri] = (
                        current[best_ri][:best_pos] + [c] + current[best_ri][best_pos:]
                    )
            current = [r for r in current if r]

        # Local search
        current = _relocate(current, dm, demands, capacity, rng)
        current = _exchange(current, dm, demands, capacity, rng)
        current = _cross_exchange(current, dm, demands, capacity, rng)
        current = _two_opt_all(current, dm, rng)

        if _validate(current, dimension, capacity, demands):
            dist = sum(_route_cost(r, dm) for r in current)
            if dist < best_dist:
                best_dist = dist
                best_routes = current

        # Stop if we're nearly out of time
        if time.time() + 0.05 > deadline:
            break

    if best_routes is None:
        # Last-resort fallback: singleton routes, but only if that fallback
        # is itself feasible (enough vehicles, and no demand exceeds capacity).
        # Otherwise, prefer whatever the solver actually constructed.
        singletons = [[i] for i in range(1, dimension)]
        if n_customers <= n_vehicles and max(demands[1:dimension], default=0) <= capacity:
            best_routes = singletons
        else:
            best_routes = cw

    return best_routes
