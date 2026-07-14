"""Convert benchmark BPP instances to the task format.

Reads the downloaded benchmark dataset (1D/2D/3D/Real-World BPP) and converts
each input file into the 1D BPP instance format expected by the CORAL task.

For multi-dimensional instances, the first spatial dimension (length) is used
as the item size. Weight, width, height, and other constraints are dropped —
this keeps the conversion simple and the problem well-defined as 1D BPP.

Instance format:
    # bin_capacity
    <capacity>
    # n_item_types
    <n>
    <size1> <qty1>
    <size2> <qty2>
    ...

Usage:
    python convert_benchmark.py
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

HERE = Path(__file__).parent
BENCHMARK_ROOT = (
    HERE
    / "Benchmark dataset for logistic-oriented Bin Packing Problems"
    / "Benchmark dataset for logistic-oriented Bin Packing Problems"
)
HIDDEN_DIR = HERE / "taskdata" / "instances"
SEED_INSTANCES_DIR = HERE / "seed" / "instances"

CATEGORIES = ["1dBPP", "2dBPP", "3dBPP", "Real World"]


def parse_benchmark_header(lines: list[str]) -> dict:
    """Parse the benchmark comment header to extract bin dimensions."""
    info: dict = {"bin_dims": [], "max_weight": [], "max_bins": None}
    for line in lines:
        line = line.strip()
        if not line.startswith("#"):
            continue
        line = line.lstrip("#").strip()
        if "Bin dimensions" in line:
            m = re.findall(r"\(([^)]+)\)", line)
            if m:
                dims = []
                for g in m:
                    parts = [x.strip() for x in g.split(",")]
                    # Filter out non-numeric labels like "L", "L * W", etc.
                    numeric = [int(p) for p in parts if p.lstrip("-").isdigit()]
                    if numeric:
                        dims.append(tuple(numeric))
                if dims:
                    info["bin_dims"] = dims
        elif "Max weight" in line:
            m = re.findall(r"\[([^\]]+)\]", line)
            if m:
                info["max_weight"] = [
                    int(x.strip()) for x in m[0].split(",") if x.strip()
                ]
        elif "Max num of bins" in line:
            m = re.search(r"(\d+)", line)
            if m:
                info["max_bins"] = int(m.group(1))
    return info


def parse_benchmark_data(lines: list[str]) -> list[tuple[int, int]]:
    """Parse the tabular data section. Returns list of (size, quantity)
    sorted by size descending."""
    items: dict[int, int] = {}  # size -> total quantity
    in_table = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("id") or line.startswith("---"):
            in_table = True
            continue
        if not in_table:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            quantity = int(parts[1])
            size = int(parts[2])  # first spatial dimension
        except (ValueError, IndexError):
            continue
        items[size] = items.get(size, 0) + quantity
    return sorted(items.items(), key=lambda x: x[0], reverse=True)


def ffd_bins(bin_capacity: int, items: list[tuple[int, int]]) -> int:
    """Compute number of bins used by first-fit decreasing."""
    flat: list[int] = []
    for size, qty in items:
        flat.extend([size] * qty)
    flat.sort(reverse=True)

    bins: list[int] = []
    for item in flat:
        placed = False
        for bi in range(len(bins)):
            if bins[bi] >= item:
                bins[bi] -= item
                placed = True
                break
        if not placed:
            bins.append(bin_capacity - item)
    return len(bins)


def write_instance(
    path: Path, bin_capacity: int, items: list[tuple[int, int]]
) -> dict:
    """Write one BPP instance file, return its metadata."""
    total_size = sum(size * qty for size, qty in items)
    total_items = sum(qty for _, qty in items)
    lower_bound = math.ceil(total_size / bin_capacity)
    ffd = ffd_bins(bin_capacity, items)
    waste_pct = (
        100.0 * (ffd * bin_capacity - total_size) / (ffd * bin_capacity)
        if ffd > 0
        else 0.0
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# bin_capacity",
        str(bin_capacity),
        f"# n_item_types",
        str(len(items)),
    ]
    for size, qty in items:
        lines.append(f"{size} {qty}")
    path.write_text("\n".join(lines) + "\n")

    return {
        "bin_capacity": bin_capacity,
        "n_types": len(items),
        "total_items": total_items,
        "total_size": total_size,
        "lower_bound": lower_bound,
        "ffd_bins": ffd,
        "ffd_score": round(lower_bound / ffd, 6) if ffd > 0 else 0.0,
        "waste_pct": round(waste_pct, 2),
    }


def convert_instance(input_path: Path, output_dir: Path) -> tuple | None:
    """Convert a single benchmark instance. Returns (name, metadata) or None."""
    try:
        text = input_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  SKIP {input_path.name}: read error ({e})")
        return None

    lines = text.splitlines()
    header_info = parse_benchmark_header(lines)
    items = parse_benchmark_data(lines)

    if not items:
        print(f"  SKIP {input_path.name}: no items parsed")
        return None

    # Determine bin_capacity from bin dimensions (use max of first dim)
    if header_info["bin_dims"]:
        bin_capacity = max(dim[0] for dim in header_info["bin_dims"])
    else:
        bin_capacity = 1000  # fallback

    # Generate output name
    category = input_path.parent.parent.name.lower().replace(" ", "_")
    stem = input_path.stem.lower().replace(" ", "_")
    name = f"bench_{category}_{stem}"

    meta = write_instance(output_dir / f"{name}.txt", bin_capacity, items)
    print(
        f"  {name:45s} cap={bin_capacity:>5}  items={meta['total_items']:>5}  "
        f"types={meta['n_types']:>4}  LB={meta['lower_bound']:>4}  "
        f"FFD={meta['ffd_bins']:>4}  score={meta['ffd_score']:.4f}"
    )
    return name, meta


def main() -> None:
    print("=== Converting benchmark instances to BPP format ===\n")

    all_meta: dict = {}

    for category in CATEGORIES:
        input_dir = BENCHMARK_ROOT / category / "input"
        if not input_dir.is_dir():
            print(f"SKIP {category}: input dir not found at {input_dir}")
            continue
        for input_file in sorted(input_dir.glob("*.txt")):
            print(f"[{category}] {input_file.name}")
            result = convert_instance(input_file, HIDDEN_DIR)
            if result:
                all_meta[result[0]] = result[1]

    if not all_meta:
        print("\nERROR: No instances converted!")
        return

    # Write reference.json for hidden instances
    ref_path = HERE / "taskdata" / "reference.json"
    ref_path.write_text(json.dumps(all_meta, indent=2))
    print(f"\nWrote {len(all_meta)} instances to {HIDDEN_DIR}")
    print(f"Reference: {ref_path}")

    # Also copy to seed/instances for local evaluation
    SEED_INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
    seed_ref: dict = {}
    for name, meta in all_meta.items():
        src = HIDDEN_DIR / f"{name}.txt"
        dst = SEED_INSTANCES_DIR / f"{name}.txt"
        dst.write_text(src.read_text())
        seed_ref[name] = meta
    (SEED_INSTANCES_DIR / "reference.json").write_text(
        json.dumps(seed_ref, indent=2)
    )
    print(f"Copied {len(seed_ref)} instances to {SEED_INSTANCES_DIR}")

    # Print summary
    print(f"\n=== Summary ===")
    total_items = sum(m["total_items"] for m in all_meta.values())
    print(f"Instances: {len(all_meta)}")
    print(f"Total items: {total_items}")
    for name, meta in sorted(all_meta.items()):
        print(
            f"  {name:<50} items={meta['total_items']:>5}  "
            f"LB={meta['lower_bound']:>4}  FFD={meta['ffd_bins']:>4}  "
            f"score={meta['ffd_score']:.4f}"
        )


if __name__ == "__main__":
    main()
