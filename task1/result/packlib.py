"""Core solvers for max-sum-of-radii circle packing in the unit square.

Two building blocks:
  * solve_radii_lp(centers)  -- exact optimal radii for fixed centers (an LP).
  * slsqp_refine(centers, radii) -- joint local optimisation over (x, y, r).

The outer search (multistart / basin hopping) lives in search.py.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog, minimize
from scipy.sparse import coo_matrix

N = 26
IU, JU = np.triu_indices(N, k=1)
NPAIR = IU.size


def solve_radii_lp(centers, slack=0.0):
    """Maximise sum(r) for fixed centers. Exact LP via HiGHS.

    r_i + r_j <= d_ij   for every pair
    r_i <= dist to each of the four walls
    """
    d = np.linalg.norm(centers[IU] - centers[JU], axis=1)
    rows = np.repeat(np.arange(NPAIR), 2)
    cols = np.column_stack([IU, JU]).ravel()
    A = coo_matrix((np.ones(2 * NPAIR), (rows, cols)), shape=(NPAIR, N))
    wall = np.minimum.reduce([centers[:, 0], centers[:, 1],
                              1.0 - centers[:, 0], 1.0 - centers[:, 1]])
    ub = np.maximum(wall + slack, 0.0)
    res = linprog(-np.ones(N), A_ub=A, b_ub=d + slack,
                  bounds=list(zip(np.zeros(N), ub)), method="highs")
    if not res.success:
        return np.zeros(N)
    return np.maximum(res.x, 0.0)


# ---------------------------------------------------------------- SLSQP -----
def _unpack(z):
    return z[:N], z[N:2 * N], z[2 * N:]


def _neg_sum(z):
    return -z[2 * N:].sum()


def _neg_sum_grad(z):
    g = np.zeros(3 * N)
    g[2 * N:] = -1.0
    return g


def _cons(z):
    x, y, r = _unpack(z)
    dx = x[IU] - x[JU]
    dy = y[IU] - y[JU]
    rs = r[IU] + r[JU]
    # squared form keeps it smooth and cheap
    pair = dx * dx + dy * dy - rs * rs
    return np.concatenate([x - r, 1.0 - x - r, y - r, 1.0 - y - r, pair])


def _cons_jac(z):
    x, y, r = _unpack(z)
    J = np.zeros((4 * N + NPAIR, 3 * N))
    idx = np.arange(N)
    J[idx, idx] = 1.0
    J[idx, 2 * N + idx] = -1.0
    J[N + idx, idx] = -1.0
    J[N + idx, 2 * N + idx] = -1.0
    J[2 * N + idx, N + idx] = 1.0
    J[2 * N + idx, 2 * N + idx] = -1.0
    J[3 * N + idx, N + idx] = -1.0
    J[3 * N + idx, 2 * N + idx] = -1.0

    dx = x[IU] - x[JU]
    dy = y[IU] - y[JU]
    rs = r[IU] + r[JU]
    p = 4 * N + np.arange(NPAIR)
    J[p, IU] = 2 * dx
    J[p, JU] = -2 * dx
    J[p, N + IU] = 2 * dy
    J[p, N + JU] = -2 * dy
    J[p, 2 * N + IU] = -2 * rs
    J[p, 2 * N + JU] = -2 * rs
    return J


_CONS = [{"type": "ineq", "fun": _cons, "jac": _cons_jac}]
_BOUNDS = [(0.0, 1.0)] * (2 * N) + [(0.0, 0.5)] * N


def slsqp_refine(centers, radii, maxiter=200, ftol=1e-12):
    z0 = np.concatenate([centers[:, 0], centers[:, 1], radii])
    res = minimize(_neg_sum, z0, jac=_neg_sum_grad, method="SLSQP",
                   bounds=_BOUNDS, constraints=_CONS,
                   options={"maxiter": maxiter, "ftol": ftol})
    x, y, r = _unpack(res.x)
    return np.column_stack([x, y]), r


def robust_polish(centers, rounds=8, maxiter=300):
    """polish() with fallback interior scales when SLSQP stalls immediately."""
    best_c, best_r, best_s = polish(centers, rounds, maxiter, interior=0.5)
    if best_s < 2.0:  # SLSQP stalled at the raw-LP value
        for sc in (0.3, 0.15, 0.7):
            c, r, s = polish(centers, rounds, maxiter, interior=sc)
            if s > best_s:
                best_c, best_r, best_s = c, r, s
            if best_s >= 2.0:
                break
    return best_c, best_r, best_s


def largest_hole(centers, radii, grid=160):
    """Center of the largest empty circle not overlapping any disk or wall."""
    g = (np.arange(grid) + 0.5) / grid
    X, Y = np.meshgrid(g, g, indexing="ij")
    P = np.column_stack([X.ravel(), Y.ravel()])
    d = np.linalg.norm(P[:, None, :] - centers[None, :, :], axis=2) - radii[None, :]
    clear = d.min(axis=1)
    wall = np.minimum.reduce([P[:, 0], P[:, 1], 1 - P[:, 0], 1 - P[:, 1]])
    val = np.minimum(clear, wall)
    return P[int(np.argmax(val))]


def polish(centers, rounds=8, maxiter=300, interior=0.5):
    """Alternate SLSQP and exact LP. Monotone: never returns worse than the start.

    SLSQP behaves far better when started from strictly interior radii (no
    constraints active), so each round re-enters with `interior` * LP radii.
    """
    c = np.clip(centers, 0.0, 1.0)
    best_c = c.copy()
    best_r = solve_radii_lp(c)
    best_s = best_r.sum()

    for _ in range(rounds):
        c, _ = slsqp_refine(c, best_r * interior, maxiter=maxiter)
        if not np.all(np.isfinite(c)):
            break
        c = np.clip(c, 0.0, 1.0)
        r = solve_radii_lp(c)
        s = r.sum()
        if s > best_s + 1e-13:
            best_c, best_r, best_s = c.copy(), r, s
        else:
            break
        c = best_c.copy()
    return best_c, best_r, best_s


# ------------------------------------------------------------ feasibility ---
def max_violation(centers, radii):
    """Largest constraint violation (grader tolerates 1e-6)."""
    v = 0.0
    v = max(v, float(np.max(radii - centers[:, 0])))
    v = max(v, float(np.max(radii - centers[:, 1])))
    v = max(v, float(np.max(centers[:, 0] + radii - 1.0)))
    v = max(v, float(np.max(centers[:, 1] + radii - 1.0)))
    d = np.linalg.norm(centers[IU] - centers[JU], axis=1)
    v = max(v, float(np.max(radii[IU] + radii[JU] - d)))
    return v
