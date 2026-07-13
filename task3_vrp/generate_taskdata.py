"""Build a fresh, uncontaminated CVRP benchmark for the CORAL Task-3 VRP ablation.

Why: CVRPLIB Set X's optimal ROUTES are published online, and `dimension` is a
unique key across all 100 X instances (it's the first arg to `solve()`) — an
agent with web access could hardcode `{101: [...routes...]}` and score ~1.0
without solving anything. This script replaces Set X with instances generated
fresh from the XML100 generator (Uchoa et al. 2017 / Queiroga et al. 2022),
whose optimal solutions have never existed anywhere.

Pipeline:
  1. Generate N_TOTAL_INSTANCES n=100 instances, stratified across the
     generator's (depot, customer, demand, route-size) parameter space.
  2. Split into a hidden set and a disjoint public dev set, both stratified.
  3. Label every instance with PyVRP HGS: free/unlimited fleet,
     round_func='round' (proven identical to the grader's distance formula),
     best-of-3 seeds x 60s each.
  4. Independently re-validate every label against the grader's own rules
     (not PyVRP's internal feasibility flag) before writing it. Any failure
     is a hard error.
  5. Write taskdata/ (hidden, grader-private) and seed/instances/ (public dev).

Deterministic and re-runnable: every source of randomness is a fixed,
documented seed declared below.

Run: python generate_taskdata.py
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
# Committed alongside this script (7.5K) so the pipeline reproduces from a clone
# without re-downloading the 100 MB CVRPLIB corpus. Upstream source:
# https://galgos.inf.puc-rio.br/cvrplib/uploads/files/xml100/generator.py
GENERATOR = os.path.join(HERE, "generator.py")
STAGING = os.path.join(HERE, "data", "generated_taskdata")
TASKDATA_INSTANCES = os.path.join(HERE, "taskdata", "instances")
TASKDATA_REF = os.path.join(HERE, "taskdata", "reference.json")
SEED_INSTANCES = os.path.join(HERE, "seed", "instances")
SEED_REF = os.path.join(SEED_INSTANCES, "reference.json")

sys.path.insert(0, os.path.join(HERE, "data", "_labelval"))
from common import grader_cost, load_vrp, solve_hgs  # noqa: E402

N_CUSTOMERS = 100
N_TOTAL_INSTANCES = 60
N_PUBLIC = 10
N_HIDDEN = N_TOTAL_INSTANCES - N_PUBLIC

# Fixed private seeds -- documented here so the run reproduces exactly.
COMBO_SEED = 20260712        # which 60 of 378 (A,B,C,D) combos get used
SPLIT_SEED = 20260713        # hidden/public split
GEN_SEED_BASE = 900001       # generator.py randSeed = GEN_SEED_BASE + combo index

HGS_SECONDS = 60.0
HGS_SEEDS = (42, 43, 44)
WORKERS = min(16, os.cpu_count() or 4)

# Generator parameter cardinalities: A=depot(1-3) B=customer(1-3) C=demand(1-7)
# D=avg route size(1-6).
A_LEVELS = range(1, 4)
B_LEVELS = range(1, 4)
C_LEVELS = range(1, 8)
D_LEVELS = range(1, 7)
FACTORS = (("A depot", 0, A_LEVELS), ("B cust", 1, B_LEVELS),
           ("C demand", 2, C_LEVELS), ("D routesz", 3, D_LEVELS))


def _build_combo_set(n_total: int, seed: int) -> list[tuple[int, int, int, int]]:
    """Pick n_total distinct (A,B,C,D) combos, guaranteeing every level of
    every factor appears at least once."""
    rng = random.Random(seed)
    all_combos = [
        (a, b, c, d)
        for a in A_LEVELS for b in B_LEVELS for c in C_LEVELS for d in D_LEVELS
    ]

    # Deterministic coverage set: 7 combos (>= the largest factor cardinality)
    # that together cycle through every level of A, B, C, D.
    cover = [((i % 3) + 1, ((i + 1) % 3) + 1, i + 1, (i % 6) + 1) for i in range(7)]
    assert len(set(cover)) == 7, "coverage-set combos must be distinct"

    pool = [c for c in all_combos if c not in set(cover)]
    rng.shuffle(pool)
    selected = cover + pool[: n_total - len(cover)]
    assert len(selected) == n_total
    assert len(set(selected)) == n_total, "combo selection produced duplicates"

    for label, pos, levels in FACTORS:
        for lv in levels:
            assert any(s[pos] == lv for s in selected), f"{label} level {lv} missing"

    rng.shuffle(selected)
    return selected


def _generate_instances(combos: list[tuple[int, int, int, int]]) -> list[dict]:
    """Invoke the XML100 generator for each combo; rename output to G100_*."""
    if os.path.isdir(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(STAGING, exist_ok=True)

    instances = []
    for i, combo in enumerate(combos):
        a, b, c, d = combo
        gen_seed = GEN_SEED_BASE + i
        subprocess.run(
            [sys.executable, GENERATOR, str(N_CUSTOMERS),
             str(a), str(b), str(c), str(d), "1", str(gen_seed)],
            cwd=STAGING, check=True, capture_output=True, text=True,
        )
        old_name = f"XML{N_CUSTOMERS}_{a}{b}{c}{d}_01"
        old_path = os.path.join(STAGING, old_name + ".vrp")
        if not os.path.exists(old_path):
            raise RuntimeError(f"generator did not produce {old_path}")

        new_name = f"G{N_CUSTOMERS}_{a}{b}{c}{d}_01"
        assert not re.search(r"-k\d", new_name), f"forbidden -k token in {new_name}"

        text = open(old_path).read()
        text, n_sub = re.subn(r"(?m)^NAME\s*:.*$", f"NAME : {new_name}", text, count=1)
        assert n_sub == 1, f"could not rewrite NAME field in {old_path}"

        text, n_sub = re.subn(
            r"(?m)^COMMENT\s*:.*$",
            f"COMMENT : Generated CVRP instance (n={N_CUSTOMERS})",
            text, count=1,
        )
        assert n_sub == 1, f"could not rewrite COMMENT field in {old_path}"
        assert "cvrplib" not in text.lower() and "xml" not in text.lower(), (
            f"instance text for {new_name} still references source corpus"
        )

        new_path = os.path.join(STAGING, new_name + ".vrp")
        with open(new_path, "w") as f:
            f.write(text)
        os.remove(old_path)

        instances.append({"name": new_name, "path": new_path, "combo": combo})

    assert len({inst["name"] for inst in instances}) == len(instances), (
        "duplicate instance names after generation"
    )
    return instances


def _stratified_split(
    instances: list[dict], n_public: int, seed: int,
) -> tuple[list[dict], list[dict]]:
    """Disjoint public/hidden split; greedily prioritises new factor-level
    coverage into the (small) public set so it isn't clustered in one corner
    of the parameter space."""
    rng = random.Random(seed)
    order = list(range(len(instances)))
    rng.shuffle(order)

    covered: list[set] = [set(), set(), set(), set()]
    public_idx: list[int] = []
    remaining = list(order)
    while remaining and len(public_idx) < n_public:
        pick = next(
            (i for i in remaining
             if any(instances[i]["combo"][k] not in covered[k] for k in range(4))),
            remaining[0],
        )
        public_idx.append(pick)
        remaining.remove(pick)
        for k in range(4):
            covered[k].add(instances[pick]["combo"][k])

    public_set = set(public_idx)
    public = [instances[i] for i in public_idx]
    hidden = [inst for j, inst in enumerate(instances) if j not in public_set]

    assert len(public) == n_public
    assert len(hidden) == len(instances) - n_public
    assert not ({p["name"] for p in public} & {h["name"] for h in hidden}), (
        "public/hidden split is not disjoint"
    )
    return public, hidden


def _hgs_job(task: tuple[str, str, int]) -> dict:
    name, path, seed = task
    cost, routes, n_routes, feasible = solve_hgs(
        path, HGS_SECONDS, seed=seed, num_vehicles=None,  # free/unlimited fleet
    )
    return {"name": name, "seed": seed, "cost": cost, "routes": routes,
            "n_routes": n_routes, "feasible": feasible}


def _label_instances(instances: list[dict]) -> dict[str, dict]:
    """Run best-of-len(HGS_SEEDS) HGS per instance; return the min-cost
    feasible result for each."""
    tasks = [
        (inst["name"], inst["path"], s) for inst in instances for s in HGS_SEEDS
    ]
    print(
        f"  {len(instances)} instances x {len(HGS_SEEDS)} seeds x "
        f"{HGS_SECONDS:.0f}s = {len(tasks)} HGS runs on {WORKERS} workers "
        f"(~{len(tasks) * HGS_SECONDS / WORKERS / 60:.1f} min wall-clock est.)",
        flush=True,
    )

    t0 = time.time()
    by_name: dict[str, list[dict]] = {inst["name"]: [] for inst in instances}
    with Pool(WORKERS) as pool:
        for i, r in enumerate(pool.imap_unordered(_hgs_job, tasks, chunksize=1), 1):
            by_name[r["name"]].append(r)
            if i % 10 == 0 or i == len(tasks):
                print(f"    ...{i}/{len(tasks)} HGS runs done "
                      f"({time.time() - t0:.0f}s)", flush=True)

    labels = {}
    for name, results in by_name.items():
        feas = [r for r in results if r["feasible"] and r["cost"] is not None]
        if not feas:
            raise RuntimeError(
                f"HGS found NO feasible solution for {name} in any of {HGS_SEEDS}"
            )
        labels[name] = min(feas, key=lambda r: r["cost"])
    return labels


def _validate_label(inst: dict, best: dict) -> tuple[int, int, int, int]:
    """Independently re-check a label against the grader's own rules (not
    PyVRP's internal feasibility flag). Any failure is a hard error."""
    name = inst["name"]
    dim, cap, coords, dem = load_vrp(inst["path"])
    assert dim == N_CUSTOMERS + 1, f"{name}: dimension {dim} != {N_CUSTOMERS + 1}"
    routes = best["routes"]

    visited = [0] * dim
    for r in routes:
        for c in r:
            if c < 1 or c >= dim:
                raise AssertionError(f"{name}: customer index {c} out of range [1,{dim})")
            visited[c] += 1
    missing = [c for c in range(1, dim) if visited[c] == 0]
    dup = [c for c in range(1, dim) if visited[c] > 1]
    if missing or dup:
        raise AssertionError(f"{name}: missing={missing} duplicated={dup}")

    for r in routes:
        load = sum(dem[c] for c in r)
        if load > cap:
            raise AssertionError(f"{name}: route demand {load} > capacity {cap}")

    n_vehicles = dim - 1
    if len(routes) > n_vehicles:
        raise AssertionError(f"{name}: {len(routes)} routes > n_vehicles {n_vehicles}")

    recomputed = grader_cost(coords, routes)
    if recomputed != best["cost"]:
        raise AssertionError(
            f"{name}: grader_cost {recomputed} != PyVRP-reported cost {best['cost']}"
        )

    return dim, cap, n_vehicles, sum(dem)


def _write_split(
    subset: list[dict], labels: dict[str, dict], out_dir: str, ref_path: str,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    reference = {}
    for inst in subset:
        best = labels[inst["name"]]
        dim, cap, n_vehicles, total_demand = _validate_label(inst, best)
        assert n_vehicles == dim - 1 == N_CUSTOMERS, (
            f"{inst['name']}: n_vehicles {n_vehicles} != dimension-1 ({dim - 1})"
        )
        shutil.copyfile(inst["path"], os.path.join(out_dir, inst["name"] + ".vrp"))
        reference[inst["name"]] = {
            "dimension": dim,
            "capacity": cap,
            "n_customers": dim - 1,
            "n_vehicles": n_vehicles,
            "total_demand": total_demand,
            "bks_distance": best["cost"],
            "ref_n_routes": best["n_routes"],
            "abcd_group": "".join(str(x) for x in inst["combo"]),
        }
    with open(ref_path, "w") as f:
        json.dump(reference, f, indent=2, sort_keys=True)
    return reference


def _print_coverage(label: str, instances: list[dict]) -> None:
    for flabel, pos, levels in FACTORS:
        counts = {lv: sum(1 for i in instances if i["combo"][pos] == lv) for lv in levels}
        print(f"    {flabel:10s} counts {counts}")


def main() -> None:
    t_start = time.time()

    print(f"[1/6] Selecting {N_TOTAL_INSTANCES} stratified (A,B,C,D) combos "
          f"(seed={COMBO_SEED})...")
    combos = _build_combo_set(N_TOTAL_INSTANCES, COMBO_SEED)

    print(f"[2/6] Generating {len(combos)} XML{N_CUSTOMERS} instances "
          f"(gen_seed_base={GEN_SEED_BASE})...")
    instances = _generate_instances(combos)
    print(f"    generated {len(instances)} instances -> {STAGING}")
    _print_coverage("all 60", instances)

    print(f"[3/6] Splitting {N_HIDDEN} hidden / {N_PUBLIC} public "
          f"(disjoint, seed={SPLIT_SEED})...")
    public, hidden = _stratified_split(instances, N_PUBLIC, SPLIT_SEED)
    print(f"    public ({len(public)}):")
    _print_coverage("public", public)
    print(f"    hidden ({len(hidden)}):")
    _print_coverage("hidden", hidden)

    print(f"[4/6] Labeling with PyVRP HGS (free fleet, round_func='round')...")
    labels = _label_instances(instances)

    print("[5/6] Validating labels against the grader's own rules "
          "and writing outputs...")
    for d in (TASKDATA_INSTANCES, SEED_INSTANCES):
        if os.path.isdir(d):
            shutil.rmtree(d)
    hidden_ref = _write_split(hidden, labels, TASKDATA_INSTANCES, TASKDATA_REF)
    public_ref = _write_split(public, labels, SEED_INSTANCES, SEED_REF)
    print(f"    wrote {len(hidden_ref)} hidden -> {TASKDATA_INSTANCES}")
    print(f"    wrote {len(public_ref)} public -> {SEED_INSTANCES}")

    print("[6/6] Summary")
    all_ref = {**hidden_ref, **public_ref}
    costs = [e["bks_distance"] for e in all_ref.values()]
    routes = [e["ref_n_routes"] for e in all_ref.values()]
    print(f"    {len(all_ref)} instances labeled and validated")
    print(f"    label cost range: [{min(costs)}, {max(costs)}]")
    print(f"    mean reference route count: {sum(routes) / len(routes):.2f}")
    print(f"    total wall time: {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
