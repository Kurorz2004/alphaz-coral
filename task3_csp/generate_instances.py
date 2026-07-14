"""Generate hidden + visible cutting-stock instances: Falkenauer triplet instances.

Falkenauer (1996) "A Hybrid Grouping Genetic Algorithm for Bin Packing" introduced
the triplet benchmark — the classic hard-instance family for 1D bin packing.

Construction (capacity = 1000):
  1. s1 ~ Uniform[380, 490]            — the "big" item
  2. s2 ~ Uniform[250, (1000-s1)/2)    — a "small" item
  3. s3 = 1000 - s1 - s2               — the second "small" item (deterministic)

Each triplet (s1, s2, s3) sums to exactly 1000. The optimal packing uses n/3 bins
and is known exactly. Items are shuffled before writing so the triplet structure
is hidden — the solver sees only a list of (length, quantity) pairs.

Why FFD fails:
- All items in [250, 500]. FFD sorts descending, pairs two largest items first.
- 490+490=980 looks excellent (2% waste), but leaves the ~260 items orphaned.
- Without their big partner, small items (s2+s3 ≈ 510-620) can't fill a bin alone.
- FFD systematically scores ~0.78-0.85 (vs optimal 1.0).

Why this works for the Task 3 ablation:
- Known optimal = n/3 bins (zero waste at the bound) → score ceiling is exactly 1.0.
- FFD scores 0.78-0.85 → ~15-22% headroom, comparable to Task 2's JSSP gap.
- The triplet structure is discoverable (agents can notice items sum to 1000 in threes).
- Finding the optimal partition is the 3-partition problem (strongly NP-hard).
- Knowledge sharing helps: one agent discovers partial triplets, shares via notes,
  the other agent uses them → CONDITION A should show a measurable deficit.

Instance sizes:
  small:  120 items (40 triplets)  — optimal 40 bins
  medium: 240 items (80 triplets)  — optimal 80 bins
  large:  360 items (120 triplets) — optimal 120 bins

Run once to (re)generate everything::

    python generate_instances.py

Instance file format::

    stock_length
    n_order_types
    length0 quantity0
    length1 quantity1
    ...
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
VISIBLE_DIR = HERE / "seed" / "instances"
HIDDEN_DIR = HERE / "taskdata" / "instances"
STOCK_LENGTH = 1000


def _generate_triplets(rng: random.Random, n_triplets: int) -> list[tuple[int, int, int]]:
    """Generate n_triplets Falkenauer triplets. Each sums to exactly STOCK_LENGTH."""
    triplets: list[tuple[int, int, int]] = []
    for _ in range(n_triplets):
        s1 = rng.randint(380, 490)              # the "big" item
        remaining = STOCK_LENGTH - s1
        # s2 ∈ [250, remaining/2) ensures s3 ≥ s2 and s3 ∈ [250, 500]
        s2_hi = max(251, remaining // 2)
        if remaining % 2 == 1:
            s2_hi = remaining // 2  # floor: keep s2 < remaining/2
        s2_lo = 250
        if s2_hi <= s2_lo:
            # rare edge case: s1 is so large that remaining/2 < 250
            # shrink s1 until there's room for two items ≥ 250
            s1 = STOCK_LENGTH - 500  # leave exactly 500 for s2+s3 (both ≥250)
            s2 = 250
            s3 = 250
        else:
            s2 = rng.randint(s2_lo, s2_hi - 1)
            s3 = remaining - s2
        triplets.append((s1, s2, s3))
    return triplets


def _write_instance(path: Path, stock_length: int, orders: list[tuple[int, int]]) -> dict:
    """Write one instance file, return its metadata."""
    total_length = sum(length * qty for length, qty in orders)
    total_items = sum(qty for _, qty in orders)
    lb_volume = math.ceil(total_length / stock_length)

    w = stock_length
    large = sum(qty for length, qty in orders if length > w / 2)
    exact_half = sum(qty for length, qty in orders if length == w / 2)
    lb_l2 = large + math.ceil(exact_half / 2)
    leftover = sum((w - length) * qty for length, qty in orders if length > w / 2)
    medium_vol = sum(length * qty for length, qty in orders if w / 3 < length <= w / 2)
    if medium_vol > leftover:
        lb_l2 += math.ceil((medium_vol - leftover) / w)

    lower_bound = max(lb_volume, lb_l2)

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# stock_length", str(stock_length), f"# n_order_types", str(len(orders))]
    for length, qty in orders:
        lines.append(f"{length} {qty}")
    path.write_text("\n".join(lines) + "\n")

    return {
        "stock_length": stock_length,
        "n_order_types": len(orders),
        "total_items": total_items,
        "total_length": total_length,
        "lb_volume": lb_volume,
        "lb_l2": lb_l2,
        "lower_bound": lower_bound,
        "waste_bound_pct": (
            100.0 * (lower_bound * stock_length - total_length) / (lower_bound * stock_length)
            if lower_bound > 0 else 0.0
        ),
    }


def _triplets_to_orders(triplets: list[tuple[int, int, int]], rng: random.Random) -> list[tuple[int, int]]:
    """Flatten triplets into (length, quantity) pairs, shuffled.

    Items are shuffled individually (not as triplets) so the triplet structure
    is hidden from the solver. Quantities are combined for duplicate lengths.
    """
    items: list[int] = []
    for s1, s2, s3 in triplets:
        items.extend([s1, s2, s3])
    rng.shuffle(items)

    counts = Counter(items)
    # Return sorted by length descending (the standard format)
    return sorted(counts.items(), key=lambda x: x[0], reverse=True)


def main() -> None:
    VISIBLE_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)

    visible_specs = [
        # (name, n_triplets, seed)
        ("train_small_a",  40,  1001),
        ("train_small_b",  40,  1002),
        ("train_medium_a", 80,  1003),
        ("train_medium_b", 80,  1004),
        ("train_large_a",  120, 1005),
        ("train_large_b",  120, 1006),
    ]

    visible_ref = {}
    print("=== visible instances ===")
    for name, n_triplets, seed in visible_specs:
        rng = random.Random(seed)
        triplets = _generate_triplets(rng, n_triplets)
        orders = _triplets_to_orders(triplets, rng)
        meta = _write_instance(VISIBLE_DIR / f"{name}.txt", STOCK_LENGTH, orders)
        visible_ref[name] = meta
        n_items = meta["total_items"]
        n_types = meta["n_order_types"]
        print(f"  {name:20s} {n_triplets:>4} triplets, {n_items:>5} items, {n_types:>4} types, "
              f"LB={meta['lower_bound']:>4}, optimal={n_triplets}, "
              f"bound-waste={meta['waste_bound_pct']:.1f}%")

    (HERE / "seed" / "instances" / "reference.json").write_text(
        json.dumps(visible_ref, indent=2)
    )

    hidden_specs = [
        # (name, n_triplets, seed)
        ("gen_small_a",  40,  2001),
        ("gen_small_b",  40,  2002),
        ("gen_small_c",  40,  2003),
        ("gen_medium_a", 80,  2004),
        ("gen_medium_b", 80,  2005),
        ("gen_medium_c", 80,  2006),
        ("gen_large_a",  120, 2007),
        ("gen_large_b",  120, 2008),
        ("gen_large_c",  120, 2009),
    ]

    hidden_ref = {}
    print("\n=== hidden instances ===")
    for name, n_triplets, seed in hidden_specs:
        rng = random.Random(seed)
        triplets = _generate_triplets(rng, n_triplets)
        orders = _triplets_to_orders(triplets, rng)
        meta = _write_instance(HIDDEN_DIR / f"{name}.txt", STOCK_LENGTH, orders)
        hidden_ref[name] = meta
        n_items = meta["total_items"]
        n_types = meta["n_order_types"]
        print(f"  {name:20s} {n_triplets:>4} triplets, {n_items:>5} items, {n_types:>4} types, "
              f"LB={meta['lower_bound']:>4}, optimal={n_triplets}, "
              f"bound-waste={meta['waste_bound_pct']:.1f}%")

    (HERE / "taskdata" / "reference.json").write_text(
        json.dumps(hidden_ref, indent=2)
    )

    print(f"\nwrote {len(visible_specs)} visible + {len(hidden_specs)} hidden instances")
    visible_total_items = sum(v["total_items"] for v in visible_ref.values())
    hidden_total_items = sum(v["total_items"] for v in hidden_ref.values())
    print(f"visible: {visible_total_items} total items across {len(visible_specs)} instances")
    print(f"hidden:  {hidden_total_items} total items across {len(hidden_specs)} instances")


if __name__ == "__main__":
    main()
