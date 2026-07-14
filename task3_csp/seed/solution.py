"""Bin-packing solver: pattern enumeration (for large-item instances) + SA local search.

Must define:

    solve(bin_capacity, items, time_limit, seed) -> bins
"""

from __future__ import annotations

import math
import random
import time


# ---------------------------------------------------------------------------
# Flat-list helpers
# ---------------------------------------------------------------------------

def _expand(items: list[tuple[int, int]]) -> tuple[list[int], list[int]]:
    """Expand (size, qty) into flat (item_sizes, type_indices)."""
    sizes: list[int] = []
    indices: list[int] = []
    for idx, (size, qty) in enumerate(items):
        for _ in range(qty):
            sizes.append(size)
            indices.append(idx)
    return sizes, indices


# ---------------------------------------------------------------------------
# Greedy construction heuristics
# ---------------------------------------------------------------------------

def _ffd(
    cap: int, sizes: list[int], idxs: list[int],
) -> list[list[int]]:
    """First-fit decreasing."""
    order = sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True)
    bins: list[list[int]] = []
    rem: list[int] = []
    for i in order:
        sz = sizes[i]
        placed = False
        for bi in range(len(bins)):
            if rem[bi] >= sz:
                bins[bi].append(idxs[i])
                rem[bi] -= sz
                placed = True
                break
        if not placed:
            bins.append([idxs[i]])
            rem.append(cap - sz)
    return bins


def _bfd(
    cap: int, sizes: list[int], idxs: list[int],
) -> list[list[int]]:
    """Best-fit decreasing."""
    order = sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True)
    bins: list[list[int]] = []
    rem: list[int] = []
    for i in order:
        sz = sizes[i]
        best_bi = -1
        best_rem = cap + 1
        for bi in range(len(bins)):
            if best_rem > rem[bi] >= sz:
                best_rem = rem[bi]
                best_bi = bi
        if best_bi >= 0:
            bins[best_bi].append(idxs[i])
            rem[best_bi] -= sz
        else:
            bins.append([idxs[i]])
            rem.append(cap - sz)
    return bins


def _pack_best_fit_group(
    cap: int, sizes: list[int], idxs: list[int],
) -> list[list[int]]:
    """Build each bin by starting with the largest item, then best-fitting
    complementary items until no more fit."""
    remaining = list(range(len(sizes)))
    remaining.sort(key=lambda i: sizes[i], reverse=True)
    bins: list[list[int]] = []

    while remaining:
        largest = remaining.pop(0)
        bin_items = [idxs[largest]]
        bin_rem = cap - sizes[largest]

        while True:
            best_i = -1
            best_sz = -1
            for ri, idx in enumerate(remaining):
                sz = sizes[idx]
                if best_sz < sz <= bin_rem:
                    best_sz = sz
                    best_i = ri
            if best_i < 0:
                break
            idx = remaining.pop(best_i)
            bin_items.append(idxs[idx])
            bin_rem -= sizes[idx]

        bins.append(bin_items)

    return bins


# ---------------------------------------------------------------------------
# Pattern enumeration for large-item instances
# ---------------------------------------------------------------------------

def _gen_patterns(
    cap: int, items: list[tuple[int, int]], max_per_bin: int,
) -> list[tuple[int, ...]]:
    """Enumerate all feasible canonical patterns (sorted type-index tuples)."""
    sizes = [sz for sz, _ in items]
    n = len(items)
    seen: set[tuple[int, ...]] = set()

    def dfs(start: int, cur: list[int], cur_sum: int) -> None:
        if cur:
            seen.add(tuple(sorted(cur)))
        if len(cur) >= max_per_bin:
            return
        for i in range(start, n):
            if cur_sum + sizes[i] <= cap:
                cur.append(i)
                dfs(i, cur, cur_sum + sizes[i])
                cur.pop()

    dfs(0, [], 0)
    result = list(seen)
    result.sort(key=lambda p: sum(sizes[i] for i in p), reverse=True)
    return result


def _greedy_cover(
    patterns: list[tuple[int, ...]],
    item_qtys: list[int],
    item_sizes: list[int],
    rng: random.Random,
    noise: float = 0.0,
) -> list[tuple[int, ...]] | None:
    """Greedy set cover. Returns list of patterns, or None if bug detected."""
    remaining = list(item_qtys)
    total = sum(remaining)
    selected: list[tuple[int, ...]] = []

    while total > 0:
        best_pat: tuple[int, ...] | None = None
        best_score = -1.0

        for pat in patterns:
            feasible = True
            for idx in pat:
                if remaining[idx] <= 0:
                    feasible = False
                    break
            if not feasible:
                continue
            # Check multiplicities: pattern may need 2+ of same type
            need: dict[int, int] = {}
            for idx in pat:
                need[idx] = need.get(idx, 0) + 1
            for idx, cnt in need.items():
                if remaining[idx] < cnt:
                    feasible = False
                    break
            if not feasible:
                continue
            fill = float(sum(item_sizes[i] for i in pat))
            score = fill + rng.uniform(0, noise)
            if score > best_score:
                best_score = score
                best_pat = pat

        if best_pat is None:
            for i in range(len(remaining)):
                while remaining[i] > 0:
                    selected.append((i,))
                    remaining[i] -= 1
                    total -= 1
            break

        selected.append(best_pat)
        for idx in best_pat:
            remaining[idx] -= 1
            total -= 1

    # Validate
    counts = [0] * len(item_qtys)
    for pat in selected:
        for idx in pat:
            counts[idx] += 1
    for i, expected in enumerate(item_qtys):
        if counts[i] != expected:
            return None
    return selected


def _greedy_cover_lookahead(
    patterns: list[tuple[int, ...]],
    item_qtys: list[int],
    item_sizes: list[int],
    cap: int,
    rng: random.Random,
    noise: float = 10.0,
) -> list[tuple[int, ...]] | None:
    """Greedy set cover with lookahead: pick pattern minimizing LB on remaining bins.

    LB_remaining = ceil(sum(remaining item sizes) / capacity).
    Pick the pattern that minimizes (1 + LB_remaining), i.e., minimizes
    the expected total bins after this choice.

    With noise, occasionally picks suboptimal patterns for diversity.
    """
    remaining = list(item_qtys)
    total_rem = sum(remaining)
    selected: list[tuple[int, ...]] = []

    while total_rem > 0:
        best_pat: tuple[int, ...] | None = None
        best_score = float('inf')

        # Compute total remaining size for LB calculation
        total_rem_size = sum(remaining[i] * item_sizes[i] for i in range(len(remaining)))

        # Score each feasible pattern
        candidates: list[tuple[float, tuple[int, ...]]] = []
        for pat in patterns:
            # Check feasibility and multiplicity
            feasible = True
            need: dict[int, int] = {}
            for idx in pat:
                need[idx] = need.get(idx, 0) + 1
            for idx, cnt in need.items():
                if remaining[idx] < cnt:
                    feasible = False
                    break
            if not feasible:
                continue

            # Compute remaining items after using this pattern
            new_rem_size = total_rem_size - sum(item_sizes[i] for i in pat)
            lb_remaining = (new_rem_size + cap - 1) // cap
            expected_bins = 1 + lb_remaining
            # Add small noise for diversity
            score = expected_bins + rng.uniform(0, noise) / 100.0
            candidates.append((score, pat))

        if not candidates:
            for i in range(len(remaining)):
                while remaining[i] > 0:
                    selected.append((i,))
                    remaining[i] -= 1
                    total_rem -= 1
            break

        # Pick the pattern with best (lowest) expected bins
        candidates.sort(key=lambda x: x[0])
        # Top-2 selection: sometimes pick second-best for diversity
        pick = min(2, len(candidates))
        if pick > 1 and rng.random() < 0.3:
            best_pat = candidates[1][1]
        else:
            best_pat = candidates[0][1]

        selected.append(best_pat)
        for idx in best_pat:
            remaining[idx] -= 1
            total_rem -= 1
        total_rem_size -= sum(item_sizes[i] for i in best_pat)

    # Validate
    counts = [0] * len(item_qtys)
    for pat in selected:
        for idx in pat:
            counts[idx] += 1
    for i, expected in enumerate(item_qtys):
        if counts[i] != expected:
            return None
    return selected


def _greedy_cover_topk(
    patterns: list[tuple[int, ...]],
    item_qtys: list[int],
    item_sizes: list[int],
    rng: random.Random,
    noise: float = 50.0,
    top_k: int = 3,
) -> list[tuple[int, ...]] | None:
    """Greedy set cover with top-k random selection for diversity."""
    remaining = list(item_qtys)
    total = sum(remaining)
    selected: list[tuple[int, ...]] = []

    while total > 0:
        scored: list[tuple[float, tuple[int, ...]]] = []
        for pat in patterns:
            feasible = True
            for idx in pat:
                if remaining[idx] <= 0:
                    feasible = False
                    break
            if not feasible:
                continue
            # Check multiplicities: pattern may need 2+ of same type
            need: dict[int, int] = {}
            for idx in pat:
                need[idx] = need.get(idx, 0) + 1
            for idx, cnt in need.items():
                if remaining[idx] < cnt:
                    feasible = False
                    break
            if not feasible:
                continue
            fill = float(sum(item_sizes[i] for i in pat))
            scored.append((fill + rng.uniform(0, noise), pat))

        if not scored:
            for i in range(len(remaining)):
                while remaining[i] > 0:
                    selected.append((i,))
                    remaining[i] -= 1
                    total -= 1
            break

        scored.sort(key=lambda x: x[0], reverse=True)
        pick = min(top_k, len(scored))
        _, best_pat = scored[rng.randint(0, pick - 1)]

        selected.append(best_pat)
        for idx in best_pat:
            remaining[idx] -= 1
            total -= 1

    counts = [0] * len(item_qtys)
    for pat in selected:
        for idx in pat:
            counts[idx] += 1
    for i, expected in enumerate(item_qtys):
        if counts[i] != expected:
            return None
    return selected


# ---------------------------------------------------------------------------
# Simulated Annealing local search
# ---------------------------------------------------------------------------

def _bin_fills(
    bins: list[list[int]], type_sizes: list[int],
) -> list[int]:
    """Sum type_sizes[idx] for each bin, where idx is an item TYPE index."""
    return [sum(type_sizes[idx] for idx in b) for b in bins]


def _sa_improve(
    cap: int,
    type_sizes: list[int],
    bins: list[list[int]],
    rng: random.Random,
    deadline: float,
) -> list[list[int]]:
    """Simulated annealing to reduce bin count.

    NOTE: bins store item TYPE indices. type_sizes maps type_idx -> size.
    """
    cur = [list(b) for b in bins]
    cur_fills = _bin_fills(cur, type_sizes)
    n_bins = len(cur)

    def _waste(fills: list[int]) -> int:
        return sum(cap - f for f in fills)

    cur_waste = _waste(cur_fills)
    best = [list(b) for b in cur]
    best_n = n_bins
    best_waste = cur_waste

    T = 200.0
    T_min = 0.05
    cooling = 0.99995

    iteration = 0
    while time.time() < deadline and n_bins > 1:
        T = max(T * cooling, T_min)
        iteration += 1
        if iteration > 500000:
            break

        op = rng.random()

        if op < 0.4 and n_bins >= 2:
            # --- Move item ---
            src = rng.randint(0, n_bins - 1)
            if len(cur[src]) <= 1:
                continue
            src_pos = rng.randint(0, len(cur[src]) - 1)
            item = cur[src][src_pos]
            item_sz = type_sizes[item]

            dsts = [
                bi for bi in range(n_bins)
                if bi != src and cur_fills[bi] + item_sz <= cap
            ]
            if not dsts:
                continue
            dst = rng.choice(dsts)

            old_src = cur_fills[src]
            old_dst = cur_fills[dst]
            new_src = old_src - item_sz
            new_dst = old_dst + item_sz
            dw = (cap - new_src) + (cap - new_dst) - (cap - old_src) - (cap - old_dst)

            accept = dw <= 0 or rng.random() < math.exp(-dw / max(T, 0.01))
            if accept:
                cur[src].pop(src_pos)
                cur[dst].append(item)
                cur_fills[src] = new_src
                cur_fills[dst] = new_dst
                cur_waste += dw
                if n_bins < best_n or (n_bins == best_n and cur_waste < best_waste):
                    best = [list(b) for b in cur]
                    best_n = n_bins
                    best_waste = cur_waste

        elif op < 0.7 and n_bins >= 2:
            # --- Swap items ---
            src = rng.randint(0, n_bins - 1)
            dst = rng.randint(0, n_bins - 1)
            if src == dst or not cur[src] or not cur[dst]:
                continue
            sp = rng.randint(0, len(cur[src]) - 1)
            dp = rng.randint(0, len(cur[dst]) - 1)
            si = cur[src][sp]
            di = cur[dst][dp]
            nsf = cur_fills[src] - type_sizes[si] + type_sizes[di]
            ndf = cur_fills[dst] - type_sizes[di] + type_sizes[si]
            if nsf > cap or ndf > cap:
                continue
            dw = (cap - nsf) + (cap - ndf) - (cap - cur_fills[src]) - (cap - cur_fills[dst])
            accept = dw <= 0 or rng.random() < math.exp(-dw / max(T, 0.01))
            if accept:
                cur[src][sp] = di
                cur[dst][dp] = si
                cur_fills[src] = nsf
                cur_fills[dst] = ndf
                cur_waste += dw
                if n_bins < best_n or (n_bins == best_n and cur_waste < best_waste):
                    best = [list(b) for b in cur]
                    best_n = n_bins
                    best_waste = cur_waste

        elif op < 0.85 and n_bins >= 2:
            # --- Try empty a bin ---
            src = rng.randint(0, n_bins - 1)
            src_items = list(cur[src])
            temp_caps = [
                cap - cur_fills[bi] if bi != src else 0
                for bi in range(n_bins)
            ]
            moves: list[tuple[int, int]] = []
            possible = True
            for item in src_items:
                best_bi = -1
                best_rem = cap + 1
                for bi in range(n_bins):
                    if bi == src:
                        continue
                    if best_rem > temp_caps[bi] >= type_sizes[item]:
                        best_rem = temp_caps[bi]
                        best_bi = bi
                if best_bi >= 0:
                    moves.append((item, best_bi))
                    temp_caps[best_bi] -= type_sizes[item]
                else:
                    possible = False
                    break
            if possible and moves:
                for item, dst_bi in moves:
                    cur[dst_bi].append(item)
                    cur_fills[dst_bi] += type_sizes[item]
                cur.pop(src)
                cur_fills.pop(src)
                n_bins -= 1
                cur_waste = _waste(cur_fills)
                if n_bins < best_n:
                    best = [list(b) for b in cur]
                    best_n = n_bins
                    best_waste = cur_waste

        else:
            # --- Repack 2-3 bins ---
            if n_bins < 3:
                continue
            n_unpack = rng.randint(2, min(4, n_bins))
            unpack_bi = rng.sample(range(n_bins), n_unpack)
            freed: list[int] = []
            for bi in sorted(unpack_bi, reverse=True):
                freed.extend(cur[bi])
                cur.pop(bi)
                cur_fills.pop(bi)
            n_bins -= n_unpack
            freed.sort(key=lambda i: type_sizes[i], reverse=True)
            for item in freed:
                sz = type_sizes[item]
                best_bi = -1
                best_rem = cap + 1
                for bi in range(n_bins):
                    rem = cap - cur_fills[bi]
                    if best_rem > rem >= sz:
                        best_rem = rem
                        best_bi = bi
                if best_bi >= 0:
                    cur[best_bi].append(item)
                    cur_fills[best_bi] += sz
                else:
                    cur.append([item])
                    cur_fills.append(sz)
                    n_bins += 1
            cur_waste = _waste(cur_fills)
            if n_bins < best_n or (n_bins == best_n and cur_waste < best_waste):
                best = [list(b) for b in cur]
                best_n = n_bins
                best_waste = cur_waste

    return best


# ---------------------------------------------------------------------------
# Systematic bin elimination
# ---------------------------------------------------------------------------

def _try_empty_bins_systematic(
    cap: int,
    type_sizes: list[int],
    bins: list[list[int]],
) -> list[list[int]]:
    """Deterministically try to empty bins, starting from emptiest.

    For each bin, try to redistribute all its items into other bins via
    best-fit. If any bin can be emptied, repeat the process.
    """
    cur = [list(b) for b in bins]

    while True:
        if len(cur) <= 1:
            break
        improved = False

        # Compute fills and sort by item count (fewest first — easiest to empty)
        fills = [sum(type_sizes[idx] for idx in b) for b in cur]
        order = sorted(range(len(cur)), key=lambda i: len(cur[i]))

        for src_bi in order:
            if src_bi >= len(cur):
                continue
            src_items = cur[src_bi]

            # Compute capacities of all other bins
            caps = []
            for bi, b in enumerate(cur):
                if bi == src_bi:
                    caps.append(0)
                else:
                    caps.append(cap - fills[bi])

            # Try to place each item from src_bin into other bins (best-fit)
            moves: list[tuple[int, int]] = []
            possible = True
            for item in src_items:
                sz = type_sizes[item]
                best_bi = -1
                best_rem = cap + 1
                for bi in range(len(cur)):
                    if bi == src_bi:
                        continue
                    if best_rem > caps[bi] >= sz:
                        best_rem = caps[bi]
                        best_bi = bi
                if best_bi >= 0:
                    moves.append((item, best_bi))
                    caps[best_bi] -= sz
                else:
                    possible = False
                    break

            if possible:
                for item, dst_bi in moves:
                    cur[dst_bi].append(item)
                cur.pop(src_bi)
                # Recompute fills
                fills = [sum(type_sizes[idx] for idx in b) for b in cur]
                improved = True
                break

        if not improved:
            break

    return cur


def _try_redistribute_dfs(
    cap: int,
    type_sizes: list[int],
    bins: list[list[int]],
    max_tries: int = 3,
) -> list[list[int]]:
    """Try to eliminate one bin by DFS redistribution of its items.

    For each bin (starting from emptiest), try all possible ways to
    place its items into other bins. Uses DFS with best-fit heuristic
    ordering. On success, restart the process.
    """
    cur = [list(b) for b in bins]

    while len(cur) > 1:
        improved = False
        fills = [sum(type_sizes[idx] for idx in b) for b in cur]
        order = sorted(range(len(cur)), key=lambda i: len(cur[i]))

        for src_bi in order[:max_tries]:
            if src_bi >= len(cur):
                continue
            src_items = cur[src_bi]

            # Precompute target capacities and sort by tightness
            caps = [cap - fills[bi] if bi != src_bi else 0 for bi in range(len(cur))]
            target_order = sorted(
                [bi for bi in range(len(cur)) if bi != src_bi],
                key=lambda bi: caps[bi],
            )

            # DFS to find a placement for all items
            assignment: dict[int, int] = {}  # item -> dst_bi

            def dfs(item_idx: int) -> bool:
                if item_idx == len(src_items):
                    return True
                item = src_items[item_idx]
                sz = type_sizes[item]
                for bi in target_order:
                    if caps[bi] >= sz:
                        caps[bi] -= sz
                        assignment[item] = bi
                        if dfs(item_idx + 1):
                            return True
                        caps[bi] += sz
                return False

            if dfs(0):
                for item, dst_bi in assignment.items():
                    cur[dst_bi].append(item)
                cur.pop(src_bi)
                improved = True
                break

        if not improved:
            break
        fills = [sum(type_sizes[idx] for idx in b) for b in cur]

    return cur


def _try_pair_merge(
    cap: int,
    type_sizes: list[int],
    bins: list[list[int]],
) -> list[list[int]]:
    """Try to merge pairs of bins: if two bins' items fit into one bin, merge them.

    Exhaustively checks all bin pairs. If a merge is found, repeats.
    """
    cur = [list(b) for b in bins]

    while True:
        improved = False
        fills = [sum(type_sizes[idx] for idx in b) for b in cur]
        n = len(cur)

        # Sort pairs by combined fill (fullest pairs first — most likely to merge)
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((fills[i] + fills[j], i, j))
        pairs.sort(reverse=True)

        for combined_fill, i, j in pairs:
            if i >= len(cur) or j >= len(cur):
                continue
            if combined_fill <= cap:
                # Can merge into one bin
                cur[i].extend(cur[j])
                cur.pop(j)
                improved = True
                break

        if not improved:
            break

    return cur


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def _validate(
    bins: list[list[int]], cap: int, items: list[tuple[int, int]],
) -> bool:
    try:
        n = len(items)
        counts = [0] * n
        for b in bins:
            total = 0
            for idx in b:
                if idx < 0 or idx >= n:
                    return False
                total += items[idx][0]
                counts[idx] += 1
            if total > cap:
                return False
        for i, (_, qty) in enumerate(items):
            if counts[i] != qty:
                return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main solve
# ---------------------------------------------------------------------------

def solve(
    bin_capacity: int,
    items: list[tuple[int, int]],
    time_limit: float,
    seed: int,
) -> list[list[int]]:
    """Solve bin packing problem."""
    rng = random.Random(seed)
    t0 = time.time()
    deadline = t0 + time_limit * 0.95

    sizes, type_idxs = _expand(items)
    n_total = len(sizes)
    min_sz = min(sz for sz, _ in items)
    max_per_bin = bin_capacity // min_sz
    item_sizes_list = [sz for sz, _ in items]
    item_qtys = [qty for _, qty in items]

    best_bins: list[list[int]] | None = None
    best_n = n_total + 1

    # Strategy 1: Pattern enumeration (only for large-item instances)
    if max_per_bin <= 5 and n_total <= 200:
        patterns = _gen_patterns(bin_capacity, items, max_per_bin)
        if patterns:
            # Greedy with fill heuristic
            result = _greedy_cover(patterns, item_qtys, item_sizes_list, rng)
            if result is not None and len(result) < best_n:
                best_n = len(result)
                best_bins = [list(p) for p in result]

            # Lookahead greedy (minimizes LB on remaining bins — more global view)
            for _ in range(500):
                if time.time() + 0.005 > deadline:
                    break
                result = _greedy_cover_lookahead(
                    patterns, item_qtys, item_sizes_list,
                    bin_capacity, rng, noise=rng.uniform(0, 20.0),
                )
                if result is not None and len(result) < best_n:
                    best_n = len(result)
                    best_bins = [list(p) for p in result]

            # Many random restarts — greedy is fast, so exploit the budget
            max_iters = min(1500, int(time_limit * 150))
            for _ in range(max_iters):
                if time.time() + 0.005 > deadline:
                    break
                noise = rng.uniform(30.0, 150.0)
                result = _greedy_cover_topk(
                    patterns, item_qtys, item_sizes_list, rng, noise=noise,
                )
                if result is not None and len(result) < best_n:
                    best_n = len(result)
                    best_bins = [list(p) for p in result]

            # Perturbation: target low-fill patterns for removal
            if best_bins is not None and time.time() < deadline:
                for _ in range(min(200, int(time_limit * 40))):
                    if time.time() + 0.005 > deadline:
                        break
                    # Sort patterns by fill, prefer removing low-fill ones
                    pat_fills = [(sum(item_sizes_list[i] for i in p), i, p)
                                  for i, p in enumerate(best_bins)]
                    pat_fills.sort()
                    # Try different k values (2 to 4 patterns)
                    for k in [2, 3, 4]:
                        if k > len(best_bins) - 1:
                            continue
                        # Weight toward removing low-fill patterns
                        weights = [1.0 / (fill + 1) for fill, _, _ in pat_fills]
                        # Select k patterns biased toward low fill, without replacement
                        unsel_set: set[int] = set()
                        for _ in range(k):
                            # Build fresh weights excluding already-selected
                            available = [(i, 1.0 / (pat_fills[i][0] + 1))
                                          for i in range(len(pat_fills))
                                          if pat_fills[i][1] not in unsel_set]
                            total_w = sum(w for _, w in available)
                            if total_w <= 0:
                                break
                            choice = rng.choices(
                                [i for i, _ in available],
                                weights=[w / total_w for _, w in available],
                                k=1,
                            )[0]
                            unsel_set.add(pat_fills[choice][1])
                        freed_qtys = [0] * len(item_qtys)
                        for bi in sorted(unsel_set, reverse=True):
                            for idx in best_bins[bi]:
                                freed_qtys[idx] += 1
                        # Greedy repack freed items
                        temp_remaining = list(freed_qtys)
                        temp_selected = []
                        temp_total = sum(temp_remaining)
                        # Try with noise for diversity
                        noise = rng.uniform(0, 100.0)
                        while temp_total > 0:
                            best_score = -1.0
                            best_pat = None
                            for pat in patterns:
                                ok = True
                                for idx in pat:
                                    if temp_remaining[idx] <= 0:
                                        ok = False
                                        break
                                if not ok:
                                    continue
                                need = {}
                                for idx in pat:
                                    need[idx] = need.get(idx, 0) + 1
                                for idx, cnt in need.items():
                                    if temp_remaining[idx] < cnt:
                                        ok = False
                                        break
                                if not ok:
                                    continue
                                fill = float(sum(item_sizes_list[i] for i in pat))
                                score = fill + rng.uniform(0, noise)
                                if score > best_score:
                                    best_score = score
                                    best_pat = pat
                            if best_pat is None:
                                break
                            temp_selected.append(best_pat)
                            for idx in best_pat:
                                temp_remaining[idx] -= 1
                                temp_total -= 1
                        if temp_total == 0 and len(temp_selected) < k:
                            new_best = [list(best_bins[bi]) for bi in range(len(best_bins))
                                         if bi not in unsel_set]
                            for pat in temp_selected:
                                new_best.append(list(pat))
                            if len(new_best) < best_n:
                                best_n = len(new_best)
                                best_bins = new_best
                                # Recompute pat_fills for next iteration
                                break

    # Strategy 2: Construction heuristics
    for ctor in [_ffd, _bfd, _pack_best_fit_group]:
        bins = ctor(bin_capacity, sizes, type_idxs)
        if len(bins) < best_n:
            best_n = len(bins)
            best_bins = bins

    # Strategy 3: Systematic bin elimination + SA
    if best_bins is not None:
        # Systematic bin elimination (fast, deterministic)
        elim = _try_empty_bins_systematic(
            bin_capacity, item_sizes_list, best_bins,
        )
        if _validate(elim, bin_capacity, items):
            if len(elim) < best_n:
                best_n = len(elim)
                best_bins = elim
            # DFS redistribution (try harder to eliminate one bin)
            redist = _try_redistribute_dfs(bin_capacity, item_sizes_list, elim)
            if len(redist) < best_n and _validate(redist, bin_capacity, items):
                best_n = len(redist)
                best_bins = redist

            # Pair-merge
            merged = _try_pair_merge(bin_capacity, item_sizes_list, elim)
            if len(merged) < best_n and _validate(merged, bin_capacity, items):
                best_n = len(merged)
                best_bins = merged

        # SA on best result if time permits
        if time.time() < deadline:
            improved = _sa_improve(
                bin_capacity, item_sizes_list, best_bins, rng, deadline,
            )
            if len(improved) < best_n and _validate(improved, bin_capacity, items):
                best_n = len(improved)
                best_bins = improved

    # Fallback to FFD
    if best_bins is None or not _validate(best_bins, bin_capacity, items):
        best_bins = _ffd(bin_capacity, sizes, type_idxs)

    return best_bins
