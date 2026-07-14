"""Score solution.py on the PUBLIC benchmark instances.

The official score comes from `coral eval`, which grades on a *hidden* instance
set you cannot see. This harness applies the same feasibility rules and the
same scoring formula to the visible instances in `instances/`.

Score = mean of `lower_bound / num_bins_used`, where the bound is
`ceil(total_item_size / bin_capacity)`. The bound is not always tight,
so even an optimal solution scores below 1.0.

Usage:
    python evaluate_local.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from solution import solve

HERE = Path(__file__).parent
TIME_LIMIT = 15.0
BASE_SEED = 12345


def load_instance(path: Path) -> tuple[int, list[tuple[int, int]]]:
    """Load a bin packing instance. Returns (bin_capacity, items)."""
    lines = [
        ln.strip()
        for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    bin_capacity = int(lines[0])
    n_types = int(lines[1])
    items = []
    for ln in lines[2 : 2 + n_types]:
        parts = ln.split()
        items.append((int(parts[0]), int(parts[1])))
    return bin_capacity, items


def validate(
    bin_capacity: int, items: list[tuple[int, int]], bins: list[list[int]]
) -> int:
    """Return number of bins used, or raise ValueError on first violation."""
    n_types = len(items)
    used = [0] * n_types

    for bi, b in enumerate(bins):
        total = sum(items[idx][0] for idx in b)
        if total > bin_capacity:
            raise ValueError(
                f"bin {bi}: total size {total} > bin capacity {bin_capacity}"
            )
        for idx in b:
            if idx < 0 or idx >= n_types:
                raise ValueError(
                    f"bin {bi}: index {idx} out of range [0, {n_types})"
                )
            used[idx] += 1

    for i, (size, qty) in enumerate(items):
        if used[i] != qty:
            raise ValueError(
                f"item {i} (size={size}): expected {qty} items, got {used[i]}"
            )

    return len(bins)


def main() -> None:
    instances_dir = HERE / "instances"
    ref_path = instances_dir / "reference.json"
    if not ref_path.exists():
        print("No reference.json found — run convert_benchmark.py first.")
        return

    reference = json.loads(ref_path.read_text())
    ratios, rows = [], []

    for index, name in enumerate(sorted(reference)):
        inst_path = instances_dir / f"{name}.txt"
        if not inst_path.exists():
            print(f"SKIP {name}: instance file not found")
            continue

        bin_capacity, items = load_instance(inst_path)
        meta = reference[name]
        lb = meta["lower_bound"]
        n_items = meta["total_items"]

        started = time.time()
        bins = solve(bin_capacity, items, TIME_LIMIT, BASE_SEED + index)
        elapsed = time.time() - started

        n_bins = validate(bin_capacity, items, bins)
        ratio = lb / n_bins
        waste = (
            100.0
            * (n_bins * bin_capacity - meta["total_size"])
            / (n_bins * bin_capacity)
        )
        ratios.append(ratio)
        rows.append(
            (name, meta["n_types"], n_items, lb, n_bins, ratio, waste, elapsed)
        )

    if not rows:
        print("No instances to evaluate.")
        return

    print(
        f"{'instance':<45} {'types':>6} {'items':>7} {'LB':>6} {'bins':>7} "
        f"{'score':>9} {'waste%':>8} {'sec':>7}"
    )
    for name, n_types, n_items, lb, n_bins, ratio, waste, elapsed in rows:
        print(
            f"{name:<45} {n_types:>6} {n_items:>7} {lb:>6} {n_bins:>7} "
            f"{ratio:>9.6f} {waste:>7.1f}% {elapsed:>6.2f}"
        )

    score = sum(ratios) / len(ratios)
    mean_waste = sum(r[6] for r in rows) / len(rows)
    print(f"\nscore (mean LB/bins) = {score:.6f}")
    print(f"mean waste            = {mean_waste:.1f}%")


if __name__ == "__main__":
    main()
