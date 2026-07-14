"""
Generate HARD cutting-stock instances: uniform random items in [250, 500].

Design rationale (after testing many strategies):
1. Pure Falkenauer triplets (v4): FFD=0.857 but agents crack them in eval 1
   by discovering "items sum to 1000 in threes" → hash-map enumeration → 0.985.
2. Triplets + decoys: decoys backfired — helped FFD (0.868 vs 0.857).
3. Narrow bands [300,400]: FFD=0.842, but much of the headroom is loose lower
   bound (items >W/3 can't fit 3/bin, but volume LB assumes they can).
4. Bimodal/trimodal: FFD=0.90-0.94 — not enough headroom.

Winner: uniform random [250, 500].
- FFD score ~0.900 (10% headroom over volume lower bound)
- The "triplet enumeration" heuristic agents used on pure triplets is WORSE
  than FFD on random instances (-14%!) because random items don't form clean
  triples summing to 1000.
- No discoverable combinatorial structure — improvement requires writing
  genuinely better algorithms (local search, column generation, etc.).
- Knowledge sharing between agents accelerates iterative algorithmic
  improvement across evals — exactly what the ablation needs to measure.

Instance sizes (9 hidden, same as the original task):
- 3 × small:  400 items (~150K total length, ~150 volume LB)
- 3 × medium: 600 items (~225K total length, ~225 volume LB)
- 3 × large:  800 items (~300K total length, ~300 volume LB)
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
STOCK_LENGTH = 1000


def _improved_lower_bound(orders: list[tuple[int, int]]) -> int:
    """Tighter lower bound: volume bound + per-k-item constraints + Martello-Toth L2."""
    w = STOCK_LENGTH
    total_volume = sum(length * qty for length, qty in orders)
    lb_volume = math.ceil(total_volume / w)
    best = lb_volume

    # Per-k constraint: items > w/(k+1) go at most k per bin
    items = []
    for length, qty in orders:
        items.extend([length] * qty)
    for k in range(1, 5):
        threshold = w / (k + 1)
        count = sum(1 for x in items if x > threshold)
        best = max(best, math.ceil(count / k))

    # Martello-Toth L2
    large = sum(qty for length, qty in orders if length > w / 2)
    exact_half = sum(qty for length, qty in orders if length == w / 2)
    lb2 = large + math.ceil(exact_half / 2)
    leftover = sum((w - length) * qty for length, qty in orders if length > w / 2)
    medium_vol = sum(length * qty for length, qty in orders if w / 3 < length <= w / 2)
    if medium_vol > leftover:
        lb2 += math.ceil((medium_vol - leftover) / w)

    return max(best, lb2)


def _ffd_bins(orders: list[tuple[int, int]]) -> int:
    """Return number of bins FFD uses on these orders."""
    items = []
    for idx, (length, qty) in enumerate(orders):
        items.extend([(idx, length)] * qty)
    items.sort(key=lambda x: x[1], reverse=True)
    caps = []
    for _idx, length in items:
        for si in range(len(caps)):
            if caps[si] >= length:
                caps[si] -= length
                break
        else:
            caps.append(STOCK_LENGTH - length)
    return len(caps)


def _write_instance(path: Path, stock_length: int, orders: list[tuple[int, int]]) -> dict:
    total_length = sum(length * qty for length, qty in orders)
    total_items = sum(qty for _, qty in orders)
    lower_bound = _improved_lower_bound(orders)
    ffd_bins_val = _ffd_bins(orders)
    ffd_score = lower_bound / ffd_bins_val

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
        "lower_bound": lower_bound,
        "ffd_bins": ffd_bins_val,
        "ffd_score": round(ffd_score, 6),
        "waste_pct": round(100.0 * (1 - ffd_score), 2),
    }


def _items_to_orders(items: list[int], rng: random.Random) -> list[tuple[int, int]]:
    """Shuffle items, combine duplicates into (length, quantity) pairs."""
    rng.shuffle(items)
    counts = Counter(items)
    return sorted(counts.items(), key=lambda x: x[0], reverse=True)


def main() -> None:
    out_dir = HERE / "taskdata_hard"
    inst_dir = out_dir / "instances"
    # Clean up any previous generation
    import shutil
    if out_dir.exists():
        shutil.rmtree(out_dir)
    inst_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        # Small: 400 items
        ("gen_small_a", 400, 4001),
        ("gen_small_b", 400, 4002),
        ("gen_small_c", 400, 4003),
        # Medium: 600 items
        ("gen_medium_a", 600, 4004),
        ("gen_medium_b", 600, 4005),
        ("gen_medium_c", 600, 4006),
        # Large: 800 items
        ("gen_large_a", 800, 4007),
        ("gen_large_b", 800, 4008),
        ("gen_large_c", 800, 4009),
    ]

    ref = {}
    all_ffd_scores = []

    print("=== hard instances (uniform [250, 500], no hidden structure) ===")
    for name, n_items, seed in specs:
        rng = random.Random(seed)
        items = [rng.randint(250, 500) for _ in range(n_items)]
        orders = _items_to_orders(items, rng)
        meta = _write_instance(inst_dir / f"{name}.txt", STOCK_LENGTH, orders)

        ref[name] = meta
        all_ffd_scores.append(meta["ffd_score"])
        print(f"  {name:20s} {meta['total_items']:>5} items, "
              f"{meta['n_order_types']:>4} types, "
              f"LB={meta['lower_bound']:>4}, FFD={meta['ffd_bins']:>4} bins, "
              f"score={meta['ffd_score']:.4f}, waste={meta['waste_pct']:.1f}%")

    avg_ffd = sum(all_ffd_scores) / len(all_ffd_scores)
    print(f"\n  Average FFD score: {avg_ffd:.4f} "
          f"({(1 - avg_ffd) * 100:.1f}% headroom)")

    (out_dir / "reference.json").write_text(json.dumps(ref, indent=2))
    print(f"\nWrote {len(specs)} hard instances to {out_dir}")
    total_items = sum(v["total_items"] for v in ref.values())
    print(f"Total: {total_items} items across {len(specs)} instances")


if __name__ == "__main__":
    main()
