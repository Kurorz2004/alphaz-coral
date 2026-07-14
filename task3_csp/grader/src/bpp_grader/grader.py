"""Bin Packing Problem (BPP) grader — 1D.

The agent's program must define::

    solve(bin_capacity, items, time_limit, seed) -> list[list[int]]

where ``items`` is a list of ``(size, quantity)`` tuples and the return is a
list of *bins* — each bin is a list of item indices. The total occurrences of
each item index across all bins must equal that item's ``quantity``. The sum
of sizes in any bin must not exceed ``bin_capacity``.

Score = ceil(total_size / bin_capacity) / num_bins_used.

The bound is the trivial volume bound — provably unbeatable, so the score lies
in (0, 1]. Higher is strictly better.

Any infeasible or malformed solution fails the entire evaluation.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from coral.grader import TaskGrader
from coral.types import ScoreBundle


class Grader(TaskGrader):
    """Grader for 1D bin packing on a hidden, benchmark-derived instance set."""

    def get_python_command(self) -> list[str]:
        """Pin execution to the grader venv.

        The default implementation switches to ``uv run --project <codebase>``
        when the agent's repo contains a pyproject.toml, which would let the
        agent add an exact solver (ortools) and trivially win. Pinned to
        sys.executable so only the grader's declared deps are available.
        """
        return [sys.executable]

    def evaluate(self) -> ScoreBundle:
        program_file = self.args.get("program_file", "solution.py")
        time_limit = float(self.args.get("time_limit", 10.0))
        base_seed = int(self.args.get("base_seed", 12345))

        program_path = os.path.join(self.codebase_path, program_file)
        if not os.path.exists(program_path):
            return self.fail(f"Program file not found: {program_file}")

        taskdata = Path(self.private_dir) / "taskdata"
        reference_path = taskdata / "reference.json"
        if not reference_path.exists():
            return self.fail("Hidden reference.json not found")
        reference = json.loads(reference_path.read_text())

        instances = sorted(reference)
        results: list[dict] = []

        for index, name in enumerate(instances):
            instance_path = taskdata / "instances" / f"{name}.txt"
            if not instance_path.exists():
                return self.fail(f"Hidden instance missing: {name}")

            meta = reference[name]
            bin_capacity = int(meta["bin_capacity"])
            lower_bound = int(meta["lower_bound"])

            try:
                result = _run_one(
                    program_path=program_path,
                    instance_path=instance_path,
                    time_limit=time_limit,
                    seed=base_seed + index,
                    bin_capacity=bin_capacity,
                    lower_bound=lower_bound,
                    python_cmd=self.get_python_command(),
                    wall_timeout=time_limit * 3.0 + 60.0,
                )
            except subprocess.TimeoutExpired:
                return self.fail(
                    f"{name}: solve() exceeded the wall clock budget ({time_limit}s advertised)"
                )
            except Exception as exc:  # noqa: BLE001
                return self.fail(f"{name}: evaluation failed: {exc}")

            if "error" in result:
                return self.fail(f"{name}: {result['error']}")

            n_bins = int(result["n_bins"])
            if n_bins < lower_bound:
                return self.fail(
                    f"{name}: {n_bins} bins is below the lower bound {lower_bound} — "
                    "validation is wrong or the instance was mutated"
                )

            score = lower_bound / n_bins
            waste_pct = (
                100.0
                * (n_bins * bin_capacity - result["total_size"])
                / (n_bins * bin_capacity)
            )

            results.append(
                {
                    "name": name,
                    "n_bins": n_bins,
                    "lower_bound": lower_bound,
                    "score": score,
                    "waste_pct": waste_pct,
                    "seconds": result.get("seconds", 0.0),
                }
            )

        final_score = sum(r["score"] for r in results) / len(results)
        mean_waste = sum(r["waste_pct"] for r in results) / len(results)
        worst = max(results, key=lambda r: r["waste_pct"])
        total_seconds = sum(r["seconds"] for r in results)

        detail = " | ".join(
            f"{r['name']}={r['n_bins']}bins({r['waste_pct']:+.1f}% waste)"
            for r in results
        )
        explanation = (
            f"Score: {final_score:.6f} | mean waste: {mean_waste:.1f}% | "
            f"worst: {worst['name']} {worst['waste_pct']:+.1f}% | "
            f"solved {len(results)} instances in {total_seconds:.1f}s\n{detail}"
        )

        return self.score(final_score, explanation)


_CHILD = textwrap.dedent(
    """\
    import json, sys, time, importlib.util, random, math

    program_path, instance_path, time_limit, seed = (
        sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]),
    )

    # --- load instance ----------------------------------------------------------
    lines = [
        ln.strip() for ln in open(instance_path).read().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    bin_capacity = int(lines[0])
    n_types = int(lines[1])
    items = []
    for ln in lines[2 : 2 + n_types]:
        parts = ln.split()
        items.append((int(parts[0]), int(parts[1])))

    total_size = sum(size * qty for size, qty in items)
    total_n_items = sum(qty for _, qty in items)

    # --- import solver ----------------------------------------------------------
    spec = importlib.util.spec_from_file_location("solution", program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    random.seed(seed)
    started = time.time()
    try:
        bins = module.solve(bin_capacity, items, time_limit, seed)
    except Exception as exc:
        print(json.dumps({"error": f"solve() raised: {type(exc).__name__}: {exc}"}))
        sys.exit(0)
    seconds = time.time() - started

    # --- structural validation --------------------------------------------------
    if not isinstance(bins, list):
        print(json.dumps({"error": "solve() must return a list of bins"}))
        sys.exit(0)
    if not all(isinstance(b, list) for b in bins):
        print(json.dumps({"error": "each bin must be a list of item indices"}))
        sys.exit(0)
    if not all(isinstance(i, int) for b in bins for i in b):
        print(json.dumps({"error": "bin entries must be integers (item indices)"}))
        sys.exit(0)

    # --- count how many of each item index are used -----------------------------
    used = [0] * n_types
    for b in bins:
        for idx in b:
            if idx < 0 or idx >= n_types:
                print(json.dumps({"error": f"item index {idx} out of range [0, {n_types})"}))
                sys.exit(0)
            used[idx] += 1

    for i, (size, qty) in enumerate(items):
        if used[i] != qty:
            print(json.dumps({
                "error": (
                    f"item {i} (size={size}): expected {qty} items "
                    f"but {used[i]} were placed across all bins"
                )
            }))
            sys.exit(0)

    # --- validate each bin fits capacity ----------------------------------------
    for bi, b in enumerate(bins):
        total = sum(items[idx][0] for idx in b)
        if total > bin_capacity:
            print(json.dumps({
                "error": (
                    f"bin {bi}: total size {total} exceeds "
                    f"capacity {bin_capacity}"
                )
            }))
            sys.exit(0)

    n_bins = len(bins)
    lb = math.ceil(total_size / bin_capacity)

    print(json.dumps({
        "n_bins": n_bins,
        "total_size": total_size,
        "total_items": total_n_items,
        "lower_bound": lb,
        "seconds": seconds,
    }))
    """
)


def _run_one(
    *,
    program_path: str,
    instance_path: Path,
    time_limit: float,
    seed: int,
    bin_capacity: int,
    lower_bound: int,
    python_cmd: list[str],
    wall_timeout: float,
) -> dict:
    """Run and validate the agent's solver on a single instance, in isolation."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"

    completed = subprocess.run(
        [
            *python_cmd,
            "-c",
            _CHILD,
            program_path,
            str(instance_path),
            str(time_limit),
            str(seed),
        ],
        capture_output=True,
        text=True,
        timeout=wall_timeout,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip()[-2000:])

    stdout = completed.stdout.strip()
    if not stdout:
        raise RuntimeError(f"no output; stderr: {completed.stderr.strip()[-1000:]}")
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"no valid JSON in output: {stdout[-500:]}")
