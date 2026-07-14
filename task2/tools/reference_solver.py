"""Reference JSSP solver — Giffler-Thompson + Nowicki-Smutnicki tabu search.

PROVENANCE: this file is the solver CORAL's agent `captain-nemo` wrote in eval #1
of the first (superseded) Task 2 run, commit c6cbec41. It is vendored here ONLY to
compute the `best_known` field in taskdata/reference.json, which is reporting
context for the write-up. The grader never reads `best_known` — scoring uses the
exact lower bound. Nothing about the task depends on this file.
"""

from __future__ import annotations

import random
import time

# Fraction of the advertised budget we actually consume. The remainder covers
# schedule reconstruction and interpreter teardown.
_BUDGET = 0.94
# Iterations between wall-clock checks (time.time() is not free). Power of two.
_CLOCK_EVERY = 64

# Diagnostics for offline profiling; the grader never reads these.
STATS: dict[str, int] = {}


# --------------------------------------------------------------------------
# Longest-path evaluation
# --------------------------------------------------------------------------
def _evaluate(N, dur, jp, jn, mp, mn):
    """Return (r, q, cmax, sink) for the current machine orders.

    `r[o]` is the head (earliest start) of operation o, `q[o]` its tail (longest
    path from the end of o to the sink, excluding o's own duration), and `sink`
    an operation attaining the makespan.

    One Kahn sweep yields both a topological order and the heads; the tails
    follow from walking that same order backwards, which avoids a second sweep.
    """
    r = [0] * N
    indeg = [0] * N
    stack = []
    for o in range(N):
        c = 0
        if jp[o] >= 0:
            c += 1
        if mp[o] >= 0:
            c += 1
        if c:
            indeg[o] = c
        else:
            stack.append(o)

    order = []
    push = order.append
    spop = stack.pop
    spush = stack.append
    while stack:
        o = spop()
        push(o)
        e = r[o] + dur[o]
        s = jn[o]
        if s >= 0:
            if r[s] < e:
                r[s] = e
            indeg[s] -= 1
            if indeg[s] == 0:
                spush(s)
        s = mn[o]
        if s >= 0:
            if r[s] < e:
                r[s] = e
            indeg[s] -= 1
            if indeg[s] == 0:
                spush(s)

    q = [0] * N
    cmax = 0
    sink = 0
    for i in range(N - 1, -1, -1):
        o = order[i]
        t = 0
        s = jn[o]
        if s >= 0:
            t = q[s] + dur[s]
        s = mn[o]
        if s >= 0:
            u = q[s] + dur[s]
            if u > t:
                t = u
        q[o] = t
        e = r[o] + dur[o]
        if e > cmax:
            cmax = e
            sink = o

    return r, q, cmax, sink


# --------------------------------------------------------------------------
# Giffler-Thompson active schedule generation
# --------------------------------------------------------------------------
def _giffler_thompson(n, m, mach, dur, rule, rng, noise):
    """Build one active schedule; return the operation sequence per machine."""
    job_ready = [0] * n
    mach_free = [0] * m
    next_k = [0] * n
    seqs = [[] for _ in range(m)]

    work_left = [sum(dur[j * m + k] for k in range(m)) for j in range(n)]

    for _ in range(n * m):
        best_ect = None
        best_m = -1
        cands = []
        for j in range(n):
            k = next_k[j]
            if k >= m:
                continue
            o = j * m + k
            est = job_ready[j]
            f = mach_free[mach[o]]
            if f > est:
                est = f
            ect = est + dur[o]
            cands.append((o, j, est, ect))
            if best_ect is None or ect < best_ect:
                best_ect = ect
                best_m = mach[o]

        # conflict set: operations on the bottleneck machine that could start
        # strictly before that earliest completion time
        conflict = [c for c in cands if mach[c[0]] == best_m and c[2] < best_ect]

        if len(conflict) == 1:
            o, j, est, _ = conflict[0]
        elif noise and rng.random() < noise:
            o, j, est, _ = conflict[rng.randrange(len(conflict))]
        else:
            if rule == "MWKR":
                key = lambda c: (-work_left[c[1]], c[0])
            elif rule == "SPT":
                key = lambda c: (dur[c[0]], c[0])
            elif rule == "LPT":
                key = lambda c: (-dur[c[0]], c[0])
            elif rule == "LWKR":
                key = lambda c: (work_left[c[1]], c[0])
            elif rule == "MOPNR":
                key = lambda c: (next_k[c[1]], c[0])
            else:  # FIFO: earliest possible start
                key = lambda c: (c[2], c[0])
            o, j, est, _ = min(conflict, key=key)

        seqs[mach[o]].append(o)
        end = est + dur[o]
        job_ready[j] = end
        mach_free[mach[o]] = end
        work_left[j] -= dur[o]
        next_k[j] += 1

    return seqs


def _seqs_to_links(N, seqs):
    mp = [-1] * N
    mn = [-1] * N
    for seq in seqs:
        prev = -1
        for o in seq:
            mp[o] = prev
            if prev >= 0:
                mn[prev] = o
            prev = o
    return mp, mn


# --------------------------------------------------------------------------
# Critical path and the N5 neighbourhood
# --------------------------------------------------------------------------
def _critical_blocks(dur, jp, mp, r, sink, rng):
    """Extract one critical path, split into maximal same-machine blocks."""
    path = [sink]
    o = sink
    while r[o] > 0:
        a = jp[o]
        b = mp[o]
        a_ok = a >= 0 and r[a] + dur[a] == r[o]
        b_ok = b >= 0 and r[b] + dur[b] == r[o]
        if a_ok and b_ok:
            o = a if rng.random() < 0.5 else b
        elif a_ok:
            o = a
        elif b_ok:
            o = b
        else:
            break
        path.append(o)
    path.reverse()

    blocks = []
    cur = [path[0]]
    for i in range(1, len(path)):
        if mp[path[i]] == path[i - 1]:
            cur.append(path[i])
        else:
            blocks.append(cur)
            cur = [path[i]]
    blocks.append(cur)
    return blocks


def _n5_moves(blocks):
    """Nowicki-Smutnicki N5: swap the leading / trailing pair of each block."""
    nb = len(blocks)
    moves = set()
    for i, b in enumerate(blocks):
        if len(b) < 2:
            continue
        if i > 0 or nb == 1:
            moves.add((b[0], b[1]))
        if i < nb - 1 or nb == 1:
            moves.add((b[-2], b[-1]))
    return moves


def _estimate(u, v, dur, jp, jn, mp, mn, r, q):
    """Taillard's lower bound on the makespan after reversing the arc u -> v."""
    pm = mp[u]
    sm = mn[v]

    a = jp[v]
    rv = r[a] + dur[a] if a >= 0 else 0
    if pm >= 0:
        t = r[pm] + dur[pm]
        if t > rv:
            rv = t

    a = jp[u]
    ru = r[a] + dur[a] if a >= 0 else 0
    t = rv + dur[v]
    if t > ru:
        ru = t

    a = jn[u]
    qu = q[a] + dur[a] if a >= 0 else 0
    if sm >= 0:
        t = q[sm] + dur[sm]
        if t > qu:
            qu = t

    a = jn[v]
    qv = q[a] + dur[a] if a >= 0 else 0
    t = qu + dur[u]
    if t > qv:
        qv = t

    e1 = ru + dur[u] + qu
    e2 = rv + dur[v] + qv
    return e1 if e1 > e2 else e2


def _swap(mp, mn, u, v):
    """Reverse the machine arc u -> v (u, v adjacent on their machine)."""
    p = mp[u]
    s = mn[v]
    if p >= 0:
        mn[p] = v
    mp[v] = p
    mn[v] = u
    mp[u] = v
    mn[u] = s
    if s >= 0:
        mp[s] = u


def _starts_from(N, n, m, dur, jp, jn, mp, mn):
    r = _evaluate(N, dur, jp, jn, mp, mn)[0]
    return [[r[j * m + k] for k in range(m)] for j in range(n)]


# --------------------------------------------------------------------------
# Solver
# --------------------------------------------------------------------------
def solve(
    machines: list[list[int]],
    durations: list[list[int]],
    time_limit: float,
    seed: int,
) -> list[list[int]]:
    t0 = time.time()
    deadline = t0 + time_limit * _BUDGET

    n = len(machines)
    m = len(machines[0])
    N = n * m
    rng = random.Random(seed)

    mach = [0] * N
    dur = [0] * N
    for j in range(n):
        row_m = machines[j]
        row_d = durations[j]
        base = j * m
        for k in range(m):
            mach[base + k] = row_m[k]
            dur[base + k] = row_d[k]

    jp = [(-1 if o % m == 0 else o - 1) for o in range(N)]
    jn = [(-1 if o % m == m - 1 else o + 1) for o in range(N)]

    # Max machine load and max job length are both valid makespan lower bounds;
    # reaching either certifies optimality and lets us stop early.
    load = [0] * m
    for o in range(N):
        load[mach[o]] += dur[o]
    lb = max(max(load), max(sum(durations[j]) for j in range(n)))

    # ---- construction: best of many randomised Giffler-Thompson schedules ----
    rules = ("MWKR", "MOPNR", "SPT", "LPT", "LWKR", "FIFO")

    def construct(tries):
        rule = rules[tries % len(rules)]
        noise = 0.0 if tries < len(rules) else 0.25
        seqs = _giffler_thompson(n, m, mach, dur, rule, rng, noise)
        cand_mp, cand_mn = _seqs_to_links(N, seqs)
        return cand_mp, cand_mn, _evaluate(N, dur, jp, jn, cand_mp, cand_mn)[2]

    best_mp = best_mn = None
    best_cmax = 1 << 30
    init_deadline = t0 + time_limit * 0.06
    tries = 0
    while tries < 400:
        cand_mp, cand_mn, c = construct(tries)
        if c < best_cmax:
            best_cmax = c
            best_mp, best_mn = cand_mp, cand_mn
        tries += 1
        if tries >= len(rules) and time.time() > init_deadline:
            break

    if best_cmax <= lb:
        return _starts_from(N, n, m, dur, jp, jn, best_mp, best_mn)

    # ---- tabu search ----
    mp = list(best_mp)
    mn = list(best_mn)
    elite_mp, elite_mn, elite_cmax = list(mp), list(mn), best_cmax

    tabu: dict[tuple[int, int], int] = {}
    tenure_lo = 6 + n // 3
    tenure_span = 8
    stall_limit = 1500 + 30 * N
    stall = 0
    it = 0
    randrange = rng.randrange

    while True:
        if (it & (_CLOCK_EVERY - 1)) == 0 and time.time() > deadline:
            break
        it += 1

        r, q, cmax, sink = _evaluate(N, dur, jp, jn, mp, mn)

        if cmax < best_cmax:
            best_cmax = cmax
            best_mp, best_mn = list(mp), list(mn)
            stall = 0
            if cmax <= lb:
                break
        else:
            stall += 1

        if cmax < elite_cmax:
            elite_cmax = cmax
            elite_mp, elite_mn = list(mp), list(mn)

        blocks = _critical_blocks(dur, jp, mp, r, sink, rng)
        moves = _n5_moves(blocks)
        if not moves:
            # Every critical block is a single operation, so N5 is empty. Restart
            # from a fresh construction rather than surrender the time budget.
            mp, mn, _ = construct(tries)
            tries += 1
            tabu.clear()
            stall = 0
            continue

        chosen = None
        chosen_est = 1 << 30
        fallback = None
        fallback_exp = 1 << 30
        for (u, v) in moves:
            est = _estimate(u, v, dur, jp, jn, mp, mn, r, q)
            exp = tabu.get((v, u), 0)
            if exp > it and est >= best_cmax:
                # tabu and no aspiration; keep as a last resort
                if exp < fallback_exp:
                    fallback_exp = exp
                    fallback = (u, v)
                continue
            if est < chosen_est:
                chosen_est = est
                chosen = (u, v)

        if chosen is None:
            chosen = fallback
            if chosen is None:
                break

        u, v = chosen
        _swap(mp, mn, u, v)
        tabu[(u, v)] = it + tenure_lo + randrange(tenure_span)

        if stall >= stall_limit:
            # restart from the elite solution, wipe the tabu memory, and kick it
            # with a few random critical swaps to leave the basin
            mp, mn = list(elite_mp), list(elite_mn)
            tabu.clear()
            stall = 0
            r2, _, _, sink2 = _evaluate(N, dur, jp, jn, mp, mn)
            for _ in range(3):
                mv = list(_n5_moves(_critical_blocks(dur, jp, mp, r2, sink2, rng)))
                if not mv:
                    break
                a, b = mv[randrange(len(mv))]
                _swap(mp, mn, a, b)
                r2, _, _, sink2 = _evaluate(N, dur, jp, jn, mp, mn)

    STATS["iters"] = it
    STATS["cmax"] = best_cmax
    STATS["constructions"] = tries
    return _starts_from(N, n, m, dur, jp, jn, best_mp, best_mn)
