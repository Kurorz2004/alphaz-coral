"""Job-shop scheduler: non-delay construction + tabu search on the disjunctive graph.

Representation
--------------
Operation ids are ``i = j * n_machines + k`` so a job's operations are contiguous.
A solution is a set of machine sequences, stored as doubly-linked lists via
``mp[i]`` (machine predecessor) and ``ms[i]`` (machine successor).

Evaluation
----------
The makespan is the longest path in the disjunctive graph.  Heads ``r[i]``
(longest path into i) and tails ``q[i]`` (longest path out of i, inclusive of
``dur[i]``) give ``cmax = max over sources of q[source]``.

A full O(N) recomputation per move is too slow at 10,000 operations, so we keep a
valid topological order (``order`` / ``pos``) and update it incrementally.  A move
rewires one contiguous run of a machine chain, and every rewired node lies inside
the position window ``[pos[u], pos[v]]``; re-running Kahn inside that window alone
restores validity, because each node's predecessors already sit at smaller
positions.  The window stays small (mean 11/27/60 nodes at 20x20/50x50/100x100)
because ``order`` is kept sorted by head value -- a valid topological order, since
every arc strictly increases the head (all durations are >= 1).  Heads and tails
are then repaired by one forward and one backward sweep over the nodes whose value
actually changes.

That changed set is ~40% of all nodes, so the repair is only ~2-3x cheaper than a
full recompute, and it dominates the runtime.  Everything below follows from that.

Search
------
Critical path -> maximal same-machine blocks -> candidate moves, each scored by
Taillard's / Balas-Vazacopoulos' lower bound on the resulting makespan.  Because
one graph repair costs ~4.4ms at N=10000 while one estimate costs ~1us, each
repair should buy as much as it can, and the search is **size-split**:

  * N > 900: the N7 neighbourhood (move an operation to the front or the back of
    its block) plus 4 mutually non-adjacent swaps applied per repair.
  * N <= 900: the N5 neighbourhood (swap block ends), one move per repair.  These
    instances converge anyway, and a wider neighbourhood only lets the argmin pick
    whichever lower bound happens to be loosest.

See notes/_synthesis/cost-model-inversion.md.
"""

from __future__ import annotations

import time

import numpy as np

_STATS: dict = {}  # diagnostic side-channel; ignored by solve()
_BATCH: int | None = None  # sweep override; None = size-scaled default
_N5_ONLY = False  # sweep override: restrict N7 back down to the N5 neighbourhood
_ALL_PATHS: bool | None = None  # sweep override: harvest blocks from every critical path
_TENURE = (6, 10, 100)  # tabu tenure ~ U[lo, hi + N//div)
_TAILS_EVERY: int | None = None  # sweep override: refresh tails every k iterations

# --------------------------------------------------------------------------
# construction
# --------------------------------------------------------------------------


def _gt_construct(n, m, D, M, rng, noise=0.0, nondelay=True):
    """Priority-rule schedule generation with an MWKR (most work remaining) rule.

    ``nondelay`` selects the conflict set among operations that can start at the
    earliest available time t* (no machine is ever left idle while work waits);
    otherwise Giffler-Thompson *active* generation is used, whose conflict set is
    every operation on the critical machine starting before the minimum earliest
    completion time.  On square instances non-delay is much the better start --
    the idle time an active schedule permits is never recovered (captain-ahab,
    attempt aacf9b8e: 55.5% vs 68.9% mean gap).

    ``noise`` > 0 multiplies each priority by U[1, 1+noise), randomising the
    tie-breaking enough for restarts while keeping the rule's character.
    Returns the start-time matrix (n, m).
    """
    nxt = np.zeros(n, dtype=np.int64)
    job_ready = np.zeros(n, dtype=np.int64)
    mach_free = np.zeros(m, dtype=np.int64)
    rem = D.sum(axis=1).astype(np.int64)
    alive = np.ones(n, dtype=bool)
    starts = np.zeros((n, m), dtype=np.int64)
    rows = np.arange(n)
    BIG = np.int64(1) << 60

    for _ in range(n * m):
        k = np.minimum(nxt, m - 1)
        cm = M[rows, k]
        cd = D[rows, k]
        est = np.maximum(job_ready, mach_free[cm])
        if nondelay:
            e = np.where(alive, est, BIG)
            b = int(np.argmin(e))
            m_star = int(cm[b])
            conflict = alive & (cm == m_star) & (est == est[b])
        else:
            ect = np.where(alive, est + cd, BIG)
            b = int(np.argmin(ect))
            m_star = int(cm[b])
            conflict = alive & (cm == m_star) & (est < int(ect[b]))
        idx = np.flatnonzero(conflict)
        if idx.size == 1:
            pick = int(idx[0])
        else:
            pri = rem[idx].astype(np.float64)  # MWKR: most work remaining
            if noise:
                pri = pri * (1.0 + noise * rng.random(idx.size))
            pick = int(idx[int(np.argmax(pri))])

        kk = int(nxt[pick])
        s = int(est[pick])
        d = int(cd[pick])
        starts[pick, kk] = s
        mach_free[m_star] = s + d
        job_ready[pick] = s + d
        rem[pick] -= d
        nxt[pick] = kk + 1
        if kk + 1 == m:
            alive[pick] = False

    return starts


def _seqs_from_starts(n, m, mach, starts_flat):
    """Machine sequences implied by a feasible start-time vector."""
    seqs = [[] for _ in range(m)]
    for i in range(n * m):
        seqs[mach[i]].append(i)
    for s in seqs:
        s.sort(key=lambda i: starts_flat[i])
    return seqs


# --------------------------------------------------------------------------
# core search
# --------------------------------------------------------------------------


def _tabu(n, m, dur, mach, seqs, deadline, rng, stall_limit=None, batch=1, n5_only=False, all_paths=False, tails_every=1, check_incremental=False):
    N = n * m
    INF = 1 << 60
    if stall_limit is None:
        stall_limit = 4 * N

    jp = [i - 1 if i % m else -1 for i in range(N)]
    js = [i + 1 if (i % m) != m - 1 else -1 for i in range(N)]
    mp = [-1] * N
    ms = [-1] * N
    mfirst = [-1] * m
    for mi, s in enumerate(seqs):
        mfirst[mi] = s[0]
        prev = -1
        for i in s:
            mp[i] = prev
            if prev >= 0:
                ms[prev] = i
            prev = i
        ms[prev] = -1

    jlast = [j * m + m - 1 for j in range(n)]  # makespan is realised at a job's last op
    fresh_tails = [True]      # is q exact right now?
    pending_tseeds: list = []  # tail seeds accumulated while q was left stale
    r = [0] * N
    q = [0] * N
    order = list(range(N))
    pos = [0] * N
    dirty = bytearray(N)

    def full_eval():
        """Recompute r, q, order, pos from scratch.  Returns cmax."""
        indeg = [(1 if i % m else 0) + (1 if mp[i] >= 0 else 0) for i in range(N)]
        stack = [f for f in mfirst if f % m == 0]
        rr = r
        for i in range(N):
            rr[i] = 0
        topo = []
        ap = topo.append
        while stack:
            i = stack.pop()
            ap(i)
            e = rr[i] + dur[i]
            s = js[i]
            if s >= 0:
                if e > rr[s]:
                    rr[s] = e
                c = indeg[s] - 1
                indeg[s] = c
                if c == 0:
                    stack.append(s)
            s = ms[i]
            if s >= 0:
                if e > rr[s]:
                    rr[s] = e
                c = indeg[s] - 1
                indeg[s] = c
                if c == 0:
                    stack.append(s)

        if len(topo) != N:
            raise RuntimeError("disjunctive graph became cyclic")

        qq = q
        for p in range(N - 1, -1, -1):
            i = topo[p]
            a = 0
            s = js[i]
            if s >= 0:
                a = qq[s]
            s = ms[i]
            if s >= 0 and qq[s] > a:
                a = qq[s]
            qq[i] = a + dur[i]

        # A head-sorted order is topologically valid (every arc strictly
        # increases the head, as all durations are >= 1) and keeps the
        # repair window tiny.
        topo.sort(key=rr.__getitem__)
        order[:] = topo
        for p in range(N):
            pos[topo[p]] = p
        return max(rr[i] + dur[i] for i in jlast)

    def repair_window(lo, hi):
        """Restore topological validity of order[lo..hi] after one arc flip."""
        win = order[lo : hi + 1]
        deg = {}
        for x in win:
            c = 0
            p = jp[x]
            if p >= 0 and lo <= pos[p] <= hi:
                c += 1
            p = mp[x]
            if p >= 0 and lo <= pos[p] <= hi:
                c += 1
            deg[x] = c
        stack = [x for x in win if deg[x] == 0]
        out = []
        ap = out.append
        while stack:
            x = stack.pop()
            ap(x)
            s = js[x]
            if s >= 0 and lo <= pos[s] <= hi:
                deg[s] -= 1
                if deg[s] == 0:
                    stack.append(s)
            s = ms[x]
            if s >= 0 and lo <= pos[s] <= hi:
                deg[s] -= 1
                if deg[s] == 0:
                    stack.append(s)
        for idx, x in enumerate(out):
            order[lo + idx] = x
            pos[x] = lo + idx

    def incr_heads(seeds):
        """Repair heads by sweeping forward over `order` from the first seed.

        `dirty` is indexed by *position*, not by node, so `bytearray.find` locates
        the next changed node in C instead of stepping every clean slot in Python.
        That matters: the changed set is only ~23% of the graph, but it is spread
        across it, so the traversal -- not the recomputation -- was the cost.
        Successors always sit at larger positions, so one increasing pass suffices.
        """
        lo = N
        for x in seeds:
            p = pos[x]
            dirty[p] = 1
            if p < lo:
                lo = p
        find = dirty.find
        p = lo
        while True:
            p = find(1, p)
            if p < 0:
                break
            dirty[p] = 0
            x = order[p]
            a = 0
            z = jp[x]
            if z >= 0:
                a = r[z] + dur[z]
            z = mp[x]
            if z >= 0:
                t = r[z] + dur[z]
                if t > a:
                    a = t
            if a != r[x]:
                r[x] = a
                s = js[x]
                if s >= 0:
                    dirty[pos[s]] = 1
                s = ms[x]
                if s >= 0:
                    dirty[pos[s]] = 1
            p += 1

    def incr_tails(seeds):
        """Mirror of incr_heads: one decreasing pass, driven by `rfind`."""
        hi = -1
        for x in seeds:
            p = pos[x]
            dirty[p] = 1
            if p > hi:
                hi = p
        rfind = dirty.rfind
        p = hi
        while True:
            p = rfind(1, 0, p + 1)
            if p < 0:
                break
            dirty[p] = 0
            x = order[p]
            a = 0
            s = js[x]
            if s >= 0:
                a = q[s]
            s = ms[x]
            if s >= 0 and q[s] > a:
                a = q[s]
            a += dur[x]
            if a != q[x]:
                q[x] = a
                z = jp[x]
                if z >= 0:
                    dirty[pos[z]] = 1
                z = mp[x]
                if z >= 0:
                    dirty[pos[z]] = 1
            p -= 1

    def critical_blocks(cmax):
        """Walk one critical path backwards from the operation that realises cmax.

        Uses only heads, so the tails array may be stale here.
        """
        if tails_every == 1:
            # q is always exact here, so walk forwards from a critical source and
            # prefer machine successors, which yields longer blocks.  Measured
            # better than the backward walk at 20x20 (1586 vs 1605).
            start = -1
            for f in mfirst:
                if f % m == 0 and q[f] == cmax:
                    start = f
                    break
            if start < 0:
                return []
            path = [start]
            i = start
            while True:
                want = q[i] - dur[i]
                nxt = -1
                s = ms[i]
                if s >= 0 and q[s] == want:
                    nxt = s
                else:
                    s = js[i]
                    if s >= 0 and q[s] == want:
                        nxt = s
                if nxt < 0:
                    break
                path.append(nxt)
                i = nxt
        else:
            i = -1
            for x in jlast:
                if r[x] + dur[x] == cmax:
                    i = x
                    break
            if i < 0:
                return []
            path = [i]
            while True:
                nxt = -1
                p = mp[i]
                if p >= 0 and r[i] == r[p] + dur[p]:
                    nxt = p
                else:
                    p = jp[i]
                    if p >= 0 and r[i] == r[p] + dur[p]:
                        nxt = p
                if nxt < 0:
                    break
                path.append(nxt)
                i = nxt
            path.reverse()

        blocks = []
        cur = [path[0]]
        for i in path[1:]:
            if mp[i] == cur[-1]:
                cur.append(i)
            else:
                blocks.append(cur)
                cur = [i]
        blocks.append(cur)
        return [(blk, bi > 0, bi < len(blocks) - 1) for bi, blk in enumerate(blocks)]

    def critical_blocks_all(cmax):
        """Every maximal same-machine block of critical operations.

        The makespan is only reduced once *every* critical path is broken, but a
        single walked path exposes the blocks of just one of them.  Scanning for
        all critical operations costs one O(N) pass -- cheap next to the ~4.4ms
        graph repair -- and lets a batch pick moves on parallel critical paths.

        Each block is returned with the two Nowicki-Smutnicki admissibility flags:
        an operation can only shorten a path by leaving the front or the back of
        its block, so a block with no incoming critical job-arc has nothing to gain
        from a front-insertion, and symmetrically for the back.
        """
        out = []
        for i in range(N):
            if r[i] + q[i] != cmax:
                continue
            u = mp[i]
            if u >= 0 and r[u] + q[u] == cmax and r[i] == r[u] + dur[u]:
                continue  # interior of a block, not its head
            blk = [i]
            x = i
            while True:
                s = ms[x]
                if s >= 0 and r[s] + q[s] == cmax and r[s] == r[x] + dur[x]:
                    blk.append(s)
                    x = s
                else:
                    break
            if len(blk) < 2:
                continue
            b0 = blk[0]
            z = jp[b0]
            not_first = z >= 0 and r[z] + q[z] == cmax and r[b0] == r[z] + dur[z]
            bl = blk[-1]
            s = js[bl]
            not_last = s >= 0 and r[s] + q[s] == cmax and r[s] == r[bl] + dur[bl]
            out.append((blk, not_first, not_last))
        return out

    def est_forward(seg):
        """Estimate for moving seg[0] to just after seg[-1] (Balas-Vazacopoulos).

        Machine order a -> u -> w1..wk -> v -> b becomes a -> w1..wk -> v -> u -> b.
        Returns INF when the move might close a cycle.

        Feasibility: the only new backward arc is v -> u, so a cycle needs a path
        u ~> v in the new graph.  Every predecessor of u other than v has a smaller
        head, so such a path must leave u by its job successor js[u]; and a path
        js[u] ~> v would force q[js[u]] >= dur[js[u]] + q[v] > q[v].  Hence
        q[js[u]] <= q[v] proves acyclicity.
        """
        u = seg[0]
        v = seg[-1]
        su = js[u]
        if su >= 0:
            if fresh_tails[0]:
                if q[su] > q[v]:
                    return INF
            elif r[v] >= r[su] + dur[su]:
                # Heads-only variant of the same argument: a path js[u] ~> v would
                # force r[v] >= r[js[u]] + dur[js[u]].  Sound when q is stale.
                return INF
        L = len(seg)
        a = mp[u]
        b = ms[v]

        prev = (r[a] + dur[a]) if a >= 0 else 0
        rp = [0] * L
        for idx in range(1, L):  # w1..wk then v, each now one slot earlier
            x = seg[idx]
            jx = jp[x]
            val = (r[jx] + dur[jx]) if jx >= 0 else 0
            if prev > val:
                val = prev
            rp[idx] = val
            prev = val + dur[x]
        ju = jp[u]
        val = (r[ju] + dur[ju]) if ju >= 0 else 0
        if prev > val:  # u now follows v
            val = prev
        rp[0] = val

        nxt = q[b] if b >= 0 else 0
        val = q[su] if su >= 0 else 0
        if nxt > val:
            val = nxt
        qp = [0] * L
        qp[0] = val + dur[u]
        nxt = qp[0]
        for idx in range(L - 1, 0, -1):  # v then wk..w1
            x = seg[idx]
            sx = js[x]
            val = q[sx] if sx >= 0 else 0
            if nxt > val:
                val = nxt
            val += dur[x]
            qp[idx] = val
            nxt = val

        e = 0
        for idx in range(L):
            t = rp[idx] + qp[idx]
            if t > e:
                e = t
        return e

    def est_backward(seg):
        """Estimate for moving seg[-1] to just before seg[0].

        a -> u -> w1..wk -> v -> b becomes a -> v -> u -> w1..wk -> b.

        Feasibility: the new backward arc is v -> u, so a cycle needs u ~> v.
        In the new graph v's only reachable predecessor is jp[v], and any path
        u ~> jp[v] forces r[jp[v]] >= r[u] + dur[u].  Hence
        r[jp[v]] < r[u] + dur[u] proves acyclicity.
        """
        u = seg[0]
        v = seg[-1]
        jv = jp[v]
        if jv >= 0 and r[jv] >= r[u] + dur[u]:
            return INF
        L = len(seg)
        a = mp[u]
        b = ms[v]

        rp = [0] * L
        val = (r[jv] + dur[jv]) if jv >= 0 else 0
        ra = (r[a] + dur[a]) if a >= 0 else 0
        if ra > val:
            val = ra
        rp[L - 1] = val
        prev = val + dur[v]
        for idx in range(0, L - 1):  # u then w1..wk, each one slot later
            x = seg[idx]
            jx = jp[x]
            val = (r[jx] + dur[jx]) if jx >= 0 else 0
            if prev > val:
                val = prev
            rp[idx] = val
            prev = val + dur[x]

        qp = [0] * L
        nxt = q[b] if b >= 0 else 0
        for idx in range(L - 2, -1, -1):  # wk..w1 then u
            x = seg[idx]
            sx = js[x]
            val = q[sx] if sx >= 0 else 0
            if nxt > val:
                val = nxt
            val += dur[x]
            qp[idx] = val
            nxt = val
        sv = js[v]
        val = q[sv] if sv >= 0 else 0
        if qp[0] > val:
            val = qp[0]
        qp[L - 1] = val + dur[v]

        e = 0
        for idx in range(L):
            t = rp[idx] + qp[idx]
            if t > e:
                e = t
        return e

    def do_forward(seg):
        """a -> u -> w1..wk -> v -> b  becomes  a -> w1..wk -> v -> u -> b."""
        u = seg[0]
        v = seg[-1]
        a = mp[u]
        b = ms[v]
        w1 = seg[1]
        if a >= 0:
            ms[a] = w1
        else:
            mfirst[mach[u]] = w1
        mp[w1] = a
        ms[v] = u
        mp[u] = v
        ms[u] = b
        if b >= 0:
            mp[b] = u
        # heads reseed: w1, u, b changed predecessor; tails: a, u, v changed successor
        return (w1, u, b), (a, u, v)

    def do_backward(seg):
        """a -> u -> w1..wk -> v -> b  becomes  a -> v -> u -> w1..wk -> b."""
        u = seg[0]
        v = seg[-1]
        a = mp[u]
        b = ms[v]
        wk = seg[-2]
        if a >= 0:
            ms[a] = v
        else:
            mfirst[mach[u]] = v
        mp[v] = a
        ms[v] = u
        mp[u] = v
        ms[wk] = b
        if b >= 0:
            mp[b] = wk
        return (v, u, b), (a, v, wk)

    def apply_batch(sel, refresh=True):
        """Apply every move in `sel`, then repair heads and tails in one sweep.

        Batching several moves under one O(N) repair is safe when each move is a
        plain adjacent swap of two consecutive critical operations (tight head,
        r[v] == r[u] + dur[u]) and no two of them are graph-adjacent -- see
        `select`.  Insertion moves (segment longer than 2) are always applied
        alone, because the tight-head cancellation the proof relies on does not
        hold once r[v] - r[u] exceeds dur[u].
        """
        hseeds = []
        tseeds = []
        for kind, seg in sel:
            lo = pos[seg[0]]
            hi = pos[seg[-1]]
            h, t = do_forward(seg) if kind == 0 else do_backward(seg)
            repair_window(lo, hi)
            for x in h:
                if x >= 0:
                    hseeds.append(x)
            for x in t:
                if x >= 0:
                    tseeds.append(x)
        incr_heads(hseeds)
        pending_tseeds.extend(tseeds)
        if refresh:
            incr_tails(pending_tseeds)
            del pending_tseeds[:]
            fresh_tails[0] = True
        else:
            fresh_tails[0] = False
        return max(r[i] + dur[i] for i in jlast)

    def restore(bmp, bms, bfirst):
        mp[:] = bmp
        ms[:] = bms
        mfirst[:] = bfirst
        del pending_tseeds[:]
        fresh_tails[0] = True
        return full_eval()

    cmax = full_eval()
    best_cmax = cmax
    best_mp = mp[:]
    best_ms = ms[:]
    best_first = mfirst[:]

    tabu = {}
    it = 0
    moves_made = 0
    since_improve = 0
    randint = rng.integers
    tenure_lo = _TENURE[0]
    tenure_hi = _TENURE[1] + N // _TENURE[2]
    check = 0
    stamp = [-1] * N  # per-iteration "blocked" marks, avoids clearing a set

    while True:
        check += 1
        if check >= 8:
            check = 0
            if time.perf_counter() > deadline:
                break
        it += 1

        blocks = critical_blocks_all(cmax) if all_paths else critical_blocks(cmax)
        cands = []
        for blk, not_first, not_last in blocks:
            L = len(blk)
            if L < 2:
                continue
            # Only an operation leaving the front or the back of its block can
            # shorten the path through it (Nowicki-Smutnicki); moving the head of
            # the first block earlier, or the tail of the last block later, cannot.
            if not_last:
                lo_i = L - 2 if n5_only else 0
                for i in range(lo_i, L - 1):  # move blk[i] to the end of the block
                    seg = blk[i:]
                    cands.append((est_forward(seg), 0, seg))
            if not_first:
                start = 2 if (not_last and L == 2) else 1  # L==2 duplicates the swap
                hi_j = 2 if n5_only else L
                for j in range(start, min(hi_j, L)):  # move blk[j] to the block front
                    seg = blk[: j + 1]
                    cands.append((est_backward(seg), 1, seg))
        if not cands:
            break
        cands = [c for c in cands if c[0] < INF]
        if not cands:
            break
        cands.sort(key=lambda c: c[0])

        # Best admissible move first.  If it is a plain swap, keep filling the
        # batch with further swaps that are pairwise non-adjacent in the
        # disjunctive graph -- that independence is what makes a simultaneous
        # reversal provably acyclic.  An insertion goes alone.
        sel = []
        fallback = None
        for e, kind, seg in cands:
            u, v = seg[0], seg[-1]
            if tabu.get(u * N + v, 0) > it and e >= best_cmax:
                if fallback is None:
                    fallback = (kind, seg)
                continue
            if not sel:
                sel.append((kind, seg))
                if len(seg) > 2 or batch == 1:
                    break
                for x in seg:
                    stamp[x] = it
                    for y in (jp[x], js[x], mp[x], ms[x]):
                        if y >= 0:
                            stamp[y] = it
                continue
            if len(seg) != 2 or stamp[u] == it or stamp[v] == it:
                continue
            sel.append((kind, seg))
            for x in seg:
                stamp[x] = it
                for y in (jp[x], js[x], mp[x], ms[x]):
                    if y >= 0:
                        stamp[y] = it
            if len(sel) >= batch:
                break

        if not sel:
            if fallback is None:
                break
            sel = [fallback]

        for _, seg in sel:
            tabu[seg[-1] * N + seg[0]] = it + int(randint(tenure_lo, tenure_hi))
        cmax = apply_batch(sel, refresh=(tails_every == 1 or it % tails_every == 0))
        moves_made += len(sel)

        if check_incremental:
            got_r, got_q, was_fresh = r[:], q[:], fresh_tails[0]
            ref = full_eval()
            assert ref == cmax, f"cmax {cmax} != {ref}"
            assert got_r == r, "incremental heads diverged"
            if was_fresh:
                assert got_q == q, "incremental tails diverged"
            fresh_tails[0] = True
            del pending_tseeds[:]

        if cmax < best_cmax:
            best_cmax = cmax
            best_mp = mp[:]
            best_ms = ms[:]
            best_first = mfirst[:]
            since_improve = 0
        else:
            since_improve += 1
            if since_improve > stall_limit:
                cmax = restore(best_mp, best_ms, best_first)
                tabu.clear()
                since_improve = 0

    restore(best_mp, best_ms, best_first)
    _STATS["iters"] = it
    _STATS["moves"] = moves_made
    return best_cmax, r[:], it


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def solve(machines, durations, time_limit, seed):
    t0 = time.perf_counter()
    n = len(machines)
    m = len(machines[0])
    # Leave ~5% of the budget for construction overhead and emitting starts.
    deadline = t0 + max(0.5, time_limit * 0.95) - 0.05

    M = np.asarray(machines, dtype=np.int64)
    D = np.asarray(durations, dtype=np.int64)
    dur = D.reshape(-1).tolist()
    mach = M.reshape(-1).tolist()

    rng = np.random.default_rng(seed)
    starts = _gt_construct(n, m, D, M, rng, noise=0.0)
    seqs = _seqs_from_starts(n, m, mach, starts.reshape(-1).tolist())

    # One graph update costs O(N) while one move estimate costs O(1).  At large N
    # the update swamps everything, so each update should buy several independent
    # moves (batch) and the best move a wider neighbourhood can find (N7).  Small
    # instances invert that: the update is cheap, they converge under N5 anyway,
    # and a wide neighbourhood only feeds the argmin a looser lower bound to be
    # fooled by (measured: N7 costs 20x20 ~11% makespan; it gains ~1% at 100x100).
    small = n * m <= 900
    batch = _BATCH if _BATCH is not None else (1 if small else 4)
    n5_only = _N5_ONLY or small
    # Harvesting blocks from *every* critical path costs an extra O(N) scan and
    # widens the candidate set; measured worse at 10s (0.7186 vs 0.7267). Kept
    # behind the flag as a reproducible negative.
    all_paths = _ALL_PATHS if _ALL_PATHS is not None else False
    # cmax and the critical path need only heads, so tails may be refreshed lazily;
    # they are used solely to score candidate moves.  Measured on the large
    # instances: refreshing every 4th repair lifts the mean ratio 0.6878 -> 0.6933,
    # because tails cost about half of the dominant graph repair.  Small instances
    # keep exact tails: they are converged, so cheaper-but-noisier move scores only
    # cost accuracy.
    tails_every = _TAILS_EVERY if _TAILS_EVERY is not None else (1 if small else 4)
    cmax, heads, iters = _tabu(
        n, m, dur, mach, seqs, deadline, rng, batch=batch, n5_only=n5_only,
        all_paths=all_paths, tails_every=tails_every,
    )

    out = [[0] * m for _ in range(n)]
    for j in range(n):
        base = j * m
        row = out[j]
        for k in range(m):
            row[k] = heads[base + k]
    return out
