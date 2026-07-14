"""Job-shop scheduler: Giffler-Thompson multistart + tabu search on the disjunctive graph.

The search follows Nowicki & Smutnicki's TSAB lineage:

  * a solution is the processing order of each machine (a permutation per machine);
  * heads r[i] (earliest start) and tails q[i] (longest path to the sink) are obtained
    with one topological pass over the disjunctive graph;
  * the neighbourhood N5 swaps the first or last adjacent pair of every *critical block*
    -- a maximal run of consecutive critical-path operations sharing a machine. Such a
    swap can never create a cycle, so every neighbour is feasible;
  * each candidate swap is scored with Taillard's O(1) lower bound on the resulting
    makespan, so only the accepted move pays the O(n*m) recompute;
  * a tabu list forbids undoing a swap for a randomised tenure, with the usual aspiration
    criterion, and the search backtracks to the incumbent after a stall.

Everything is deterministic given `seed`.
"""

from __future__ import annotations

import random
import time

RULES = ("MWKR", "SPT", "LPT", "LWKR", "FIFO", "MOPNR")


def solve(
    machines: list[list[int]],
    durations: list[list[int]],
    time_limit: float,
    seed: int,
) -> list[list[int]]:
    t0 = time.time()
    n = len(machines)
    m = len(machines[0])
    N = n * m
    deadline = t0 + time_limit - max(0.30, 0.05 * time_limit)
    rng = random.Random(seed)

    # ---- flat operation arrays; index N is a dummy "no such operation" sentinel ----
    p = [0] * (N + 1)
    JP = [N] * (N + 1)  # job predecessor
    JS = [N] * (N + 1)  # job successor
    has_jp = [0] * N
    for j in range(n):
        base = j * m
        dj = durations[j]
        for k in range(m):
            i = base + k
            p[i] = dj[k]
            if k:
                JP[i] = i - 1
                has_jp[i] = 1
            if k + 1 < m:
                JS[i] = i + 1

    # ------------------------------------------------------------------ graph eval
    def evaluate(MP, MS):
        """Heads, tails and makespan. Returns None if the machine orders induce a cycle."""
        r = [0] * (N + 1)
        q = [0] * (N + 1)
        indeg = [0] * N
        stack = []
        for i in range(N):
            d = has_jp[i]
            if MP[i] != N:
                d += 1
            indeg[i] = d
            if not d:
                stack.append(i)

        order = []
        push = stack.append
        emit = order.append
        while stack:
            i = stack.pop()
            emit(i)
            e = r[i] + p[i]
            s = JS[i]
            if s != N:
                if r[s] < e:
                    r[s] = e
                indeg[s] -= 1
                if not indeg[s]:
                    push(s)
            s = MS[i]
            if s != N:
                if r[s] < e:
                    r[s] = e
                indeg[s] -= 1
                if not indeg[s]:
                    push(s)
        if len(order) != N:
            return None

        cmax = 0
        for idx in range(N - 1, -1, -1):
            i = order[idx]
            v = 0
            s = JS[i]
            if s != N:
                v = q[s] + p[s]
            s = MS[i]
            if s != N:
                t = q[s] + p[s]
                if t > v:
                    v = t
            q[i] = v
            t = r[i] + p[i] + v
            if t > cmax:
                cmax = t
        return cmax, r, q

    # ------------------------------------------------- Giffler-Thompson construction
    rem_tot = [sum(durations[j]) for j in range(n)]

    def gt(rule, eps):
        """One active schedule. Returns (makespan, MP, MS)."""
        mfree = [0] * m
        jready = [0] * n
        nxt = [0] * n
        rem = rem_tot[:]
        MP = [N] * (N + 1)
        MS = [N] * (N + 1)
        last = [N] * m

        for _ in range(N):
            best_ec = None
            mstar = -1
            for j in range(n):
                k = nxt[j]
                if k == m:
                    continue
                mm = machines[j][k]
                es = jready[j]
                f = mfree[mm]
                if f > es:
                    es = f
                ec = es + durations[j][k]
                if best_ec is None or ec < best_ec:
                    best_ec = ec
                    mstar = mm

            fm = mfree[mstar]
            cand = []
            for j in range(n):
                k = nxt[j]
                if k == m or machines[j][k] != mstar:
                    continue
                es = jready[j]
                if fm > es:
                    es = fm
                if es < best_ec:
                    cand.append(j)

            if len(cand) == 1:
                jj = cand[0]
            elif rng.random() < eps:
                jj = cand[rng.randrange(len(cand))]
            elif rule == "SPT":
                jj = min(cand, key=lambda j: durations[j][nxt[j]])
            elif rule == "LPT":
                jj = max(cand, key=lambda j: durations[j][nxt[j]])
            elif rule == "MWKR":
                jj = max(cand, key=lambda j: rem[j])
            elif rule == "LWKR":
                jj = min(cand, key=lambda j: rem[j])
            elif rule == "MOPNR":
                jj = max(cand, key=lambda j: m - nxt[j])
            else:  # FIFO -- earliest ready
                jj = min(cand, key=lambda j: jready[j])

            k = nxt[jj]
            es = jready[jj]
            if fm > es:
                es = fm
            d = durations[jj][k]
            mfree[mstar] = es + d
            jready[jj] = es + d
            nxt[jj] = k + 1
            rem[jj] -= d

            i = jj * m + k
            prev = last[mstar]
            MP[i] = prev
            if prev != N:
                MS[prev] = i
            last[mstar] = i

        res = evaluate(MP, MS)
        return res[0], MP, MS

    # --------------------------------------------------------------- initial solution
    best_c = None
    best_MP = best_MS = None
    for idx in range(24):
        if time.time() > deadline:
            break
        rule = RULES[idx % len(RULES)]
        eps = 0.0 if idx < len(RULES) else 0.15
        c, MP, MS = gt(rule, eps)
        if best_c is None or c < best_c:
            best_c, best_MP, best_MS = c, MP, MS

    if N <= 1 or m == 1 or n == 1 or time.time() > deadline:
        r = evaluate(best_MP, best_MS)[1]
        return [[r[j * m + k] for k in range(m)] for j in range(n)]

    # ------------------------------------------------------------------ tabu search
    MP = best_MP[:]
    MS = best_MS[:]
    cur_c, r, q = evaluate(MP, MS)
    best_c = cur_c
    best_MP, best_MS = MP[:], MS[:]

    W = N + 1
    tabu = [0] * (W * W)
    it = 0
    stall = 0
    stall_limit = max(1200, 7 * N)
    check = 0

    def kick():
        """Random adjacent machine swaps; any cycle-inducing swap is rolled back."""
        nonlocal cur_c, r, q
        for _ in range(2 + rng.randrange(4)):
            u = rng.randrange(N)
            v = MS[u]
            if v == N:
                continue
            a = MP[u]
            b = MS[v]
            if a != N:
                MS[a] = v
            MP[v] = a
            MS[v] = u
            MP[u] = v
            MS[u] = b
            if b != N:
                MP[b] = u
            if evaluate(MP, MS) is None:
                if a != N:
                    MS[a] = u
                MP[u] = a
                MS[u] = v
                MP[v] = u
                MS[v] = b
                if b != N:
                    MP[b] = v
        cur_c, r, q = evaluate(MP, MS)

    while True:
        check += 1
        if not (check & 31) and time.time() > deadline:
            break

        # ---- critical path (randomised tie-breaking between job/machine successors)
        i = -1
        for x in range(N):
            if r[x] == 0 and r[x] + p[x] + q[x] == cur_c:
                i = x
                break

        path = [i]
        while True:
            e = r[i] + p[i]
            a, b = (JS[i], MS[i]) if rng.random() < 0.5 else (MS[i], JS[i])
            nx = -1
            if a != N and r[a] == e and r[a] + p[a] + q[a] == cur_c:
                nx = a
            elif b != N and r[b] == e and r[b] + p[b] + q[b] == cur_c:
                nx = b
            if nx < 0:
                break
            path.append(nx)
            i = nx

        # ---- block decomposition of the whole path (singletons included: the
        #      "first"/"last" exclusions of N5 are indexed over *all* blocks)
        bounds = []
        s = 0
        L = len(path)
        for x in range(1, L + 1):
            if x == L or MS[path[x - 1]] != path[x]:
                bounds.append((s, x))
                s = x

        moves = []
        nb = len(bounds)
        for bi, (s, e) in enumerate(bounds):
            if e - s < 2:
                continue
            if bi > 0:
                moves.append((path[s], path[s + 1]))
            if bi < nb - 1:
                mv = (path[e - 2], path[e - 1])
                if not moves or moves[-1] != mv:
                    moves.append(mv)

        if not moves:
            # block-optimal w.r.t. N5: diversify rather than stop
            MP[:], MS[:] = best_MP, best_MS
            tabu = [0] * (W * W)
            cur_c, r, q = evaluate(MP, MS)
            kick()
            stall = 0
            continue

        # ---- Taillard O(1) evaluation of each swap
        best_est = None
        best_mv = None
        fallback_est = None
        fallback_mv = None
        for u, v in moves:
            jpu = JP[u]
            jpv = JP[v]
            mpu = MP[u]
            jsu = JS[u]
            jsv = JS[v]
            msv = MS[v]

            rv = r[jpv] + p[jpv] if jpv != N else 0
            if mpu != N:
                t = r[mpu] + p[mpu]
                if t > rv:
                    rv = t
            ru = rv + p[v]
            if jpu != N:
                t = r[jpu] + p[jpu]
                if t > ru:
                    ru = t

            qu = q[jsu] + p[jsu] if jsu != N else 0
            if msv != N:
                t = q[msv] + p[msv]
                if t > qu:
                    qu = t
            qv = qu + p[u]
            if jsv != N:
                t = q[jsv] + p[jsv]
                if t > qv:
                    qv = t

            est = rv + p[v] + qv
            t = ru + p[u] + qu
            if t > est:
                est = t

            if fallback_est is None or est < fallback_est:
                fallback_est, fallback_mv = est, (u, v)
            if (tabu[u * W + v] <= it or est < best_c) and (best_est is None or est < best_est):
                best_est, best_mv = est, (u, v)

        if best_mv is None:
            best_mv = fallback_mv

        u, v = best_mv
        # ---- apply swap: a -> u -> v -> b  becomes  a -> v -> u -> b
        a = MP[u]
        b = MS[v]
        if a != N:
            MS[a] = v
        MP[v] = a
        MS[v] = u
        MP[u] = v
        MS[u] = b
        if b != N:
            MP[b] = u

        tabu[v * W + u] = it + 6 + rng.randrange(1 + n // 2)
        it += 1

        res = evaluate(MP, MS)
        if res is None:  # cannot happen for N5, but never emit an infeasible schedule
            if a != N:
                MS[a] = u
            MP[u] = a
            MS[u] = v
            MP[v] = u
            MS[v] = b
            if b != N:
                MP[b] = v
            res = evaluate(MP, MS)
        cur_c, r, q = res

        if cur_c < best_c:
            best_c = cur_c
            best_MP, best_MS = MP[:], MS[:]
            stall = 0
        else:
            stall += 1
            if stall >= stall_limit:
                stall = 0
                MP[:], MS[:] = best_MP, best_MS
                tabu = [0] * (W * W)
                cur_c, r, q = evaluate(MP, MS)
                kick()

    r = evaluate(best_MP, best_MS)[1]
    return [[r[j * m + k] for k in range(m)] for j in range(n)]
