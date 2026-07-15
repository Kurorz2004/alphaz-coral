"""Task 3 (CVRP) — score the ablation and audit that each condition actually held.

Final score of a run = the best REAL-mode attempt score, i.e. what `coral log`
puts at the top of the leaderboard. Tune attempts are excluded: they are a
cheaper workload and CORAL hides them from the leaderboard by default.

Two metrics are reported side by side for the SAME result:
  score    = mean over the 50 hidden instances of reference_distance/solver_distance.
             HIGHER is better. The reference is a PyVRP HGS heuristic, NOT a proven
             optimum, so the score is not capped at 1.0 and 1.0 does not mean "solved".
  mean gap = mean percentage above that reference. LOWER is better.
Score compresses into a narrow 0.95-0.99 band, which makes real progress look
tiny; gap is the legible view of the identical result.

Run:  python analyze.py
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "results"
SEED_BASELINE = HERE / "seed_baseline.json"

# The ablation runs MODEL=deepseek-v4-flash, the same model task.yaml uses for
# Task 2, so the arms are comparable to it. Every pooled run must be that model;
# anything else is excluded.
TARGET_MODEL = "deepseek-v4-flash"

EXPECTED_REAL_ATTEMPTS = 12  # run.stop.max_real_attempts in task.yaml

CONDITIONS = {
    "full": "Full CORAL (control)",
    "noknowledge": "A - notes/skills disabled",
    "noheartbeat": "B - heartbeats disabled",
    "consol": "Gate + LLM consolidation",
}


@dataclass
class Run:
    runid: str
    condition: str
    path: Path
    model: str = "?"
    final_score: float | None = None
    final_gap: float | None = None
    first_score: float | None = None
    real_attempts: int = 0
    tune_attempts: int = 0
    failed_attempts: int = 0
    best_at: int | None = None
    trajectory: list[float] = field(default_factory=list)
    integrity: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Usable as a pooled sample: finished, clean, on the pooled model."""
        return (
            self.final_score is not None
            and not self.integrity
            and self.model == TARGET_MODEL
        )


def _attempts(run: Path) -> list[dict]:
    out = []
    for f in sorted((run / ".coral/public/attempts").glob("*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    out.sort(key=lambda a: a.get("timestamp", ""))
    return out


def _budget(a: dict) -> str:
    return (a.get("metadata") or {}).get("budget_class", "real")


def _gap(feedback: str | None) -> float | None:
    m = re.search(r"mean gap:\s*([+-]?[\d.]+)%", feedback or "")
    return float(m.group(1)) if m else None


def _model_of(path: Path) -> str:
    """Read the model the run ACTUALLY used from its resolved config."""
    cfg = path / ".coral/config.yaml"
    if not cfg.exists():
        return "?"
    m = re.search(r"^\s*model:\s*(\S+)", cfg.read_text(), re.M)
    return m.group(1).strip("\"'") if m else "?"


def load_run(runid: str, condition: str, path: Path) -> Run:
    r = Run(runid=runid, condition=condition, path=path, model=_model_of(path))
    att = _attempts(path)

    real = [a for a in att if _budget(a) == "real"]
    r.tune_attempts = len(att) - len(real)
    scored = [a for a in real if a.get("score") is not None]
    r.failed_attempts = len(real) - len(scored)
    r.real_attempts = len(real)

    if scored:
        best = max(scored, key=lambda a: a["score"])
        r.final_score = best["score"]
        r.final_gap = _gap(best.get("feedback"))
        r.best_at = scored.index(best) + 1
        r.first_score = scored[0]["score"]
        running = 0.0
        for a in scored:
            running = max(running, a["score"])
            r.trajectory.append(running)

    # --- integrity: anything that makes this run unfit to pool ---
    if r.final_score is None:
        r.integrity.append("no scored real attempt")
    if r.model != TARGET_MODEL:
        r.integrity.append(f"model={r.model} (pooled model is {TARGET_MODEL})")
    if r.real_attempts < EXPECTED_REAL_ATTEMPTS:
        r.integrity.append(
            f"only {r.real_attempts}/{EXPECTED_REAL_ATTEMPTS} real attempts (incomplete)"
        )
    return r


def discover() -> list[Run]:
    runs = []
    for cond in CONDITIONS:
        d = RESULTS / cond
        if not d.is_dir():
            continue
        for path in sorted(d.iterdir()):
            if not re.search(r"-s\d+$", path.name):
                continue  # skips the `latest` symlink, which Windows cannot stat
            try:
                if not path.is_dir():
                    continue
            except OSError:
                continue
            runs.append(load_run(path.name, cond, path))
    return runs


def read_baseline() -> tuple[float | None, float | None]:
    """Seed solver's score on the HIDDEN set - the floor every condition inherits.

    Committed as seed_baseline.json so this works on a fresh clone; data/ is
    gitignored, so reading only the raw log would silently degrade to
    "unavailable" for anyone who did not run it themselves.
    """
    if SEED_BASELINE.exists():
        d = json.loads(SEED_BASELINE.read_text())
        return d["score"], d["mean_gap_pct"]
    return None, None


# --- statistics --------------------------------------------------------------

def hedges_g(a: list[float], b: list[float]) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sa, sb = statistics.stdev(a), statistics.stdev(b)
    sp = math.sqrt(((na - 1) * sa**2 + (nb - 1) * sb**2) / (na + nb - 2))
    if sp == 0:
        return float("nan")
    d = (statistics.mean(a) - statistics.mean(b)) / sp
    return d * (1 - 3 / (4 * (na + nb) - 9))  # small-sample correction


def mannwhitney_exact(a: list[float], b: list[float]) -> tuple[float, float]:
    """Exact two-sided Mann-Whitney U. Returns (U, p)."""
    na, nb = len(a), len(b)
    pool = a + b

    def _u(idx: tuple[int, ...]) -> float:
        A = [pool[i] for i in idx]
        B = [pool[i] for i in range(na + nb) if i not in idx]
        return sum((x > y) + 0.5 * (x == y) for x in A for y in B)

    obs = _u(tuple(range(na)))
    mu = na * nb / 2
    allocs = list(combinations(range(na + nb), na))
    p = sum(1 for c in allocs if abs(_u(c) - mu) >= abs(obs - mu)) / len(allocs)
    return obs, p


def p_floor(na: int, nb: int) -> float:
    """Smallest two-sided p this sample size can possibly produce."""
    return 2 / math.comb(na + nb, na)


def main() -> None:
    runs = discover()
    base_score, base_gap = read_baseline()

    print("=" * 78)
    print("  Task 3 - CVRP ablation")
    print("=" * 78)
    print("  score    = mean(reference/solver) over 50 hidden instances. HIGHER better.")
    print("             Reference is a PyVRP HGS heuristic, NOT a proven optimum:")
    print("             the score is not capped at 1.0 and 1.0 does not mean 'solved'.")
    print("  mean gap = mean % above that reference. LOWER better. Same result, legible.")
    if base_score is not None:
        print(f"\n  Seed baseline (hidden set): score {base_score:.4f}  gap {base_gap:+.2f}%")
        print("  Every condition starts here.")
    else:
        print("\n  Seed baseline: UNAVAILABLE (run data/seed_hidden.log first).")

    # --- per-run ---
    print("\n" + "-" * 78)
    print("PER-RUN")
    print("-" * 78)
    print(f"{'cond':<12} {'run':<10} {'model':<8} {'score':>7} {'gap':>7} "
          f"{'att1':>7} {'real':>5} {'tune':>5} {'best@':>6}  flags")
    for r in runs:
        s = f"{r.final_score:.4f}" if r.final_score is not None else "--"
        g = f"{r.final_gap:+.2f}%" if r.final_gap is not None else "--"
        a1 = f"{r.first_score:.4f}" if r.first_score is not None else "--"
        b = str(r.best_at) if r.best_at else "--"
        flag = "; ".join(r.integrity) if r.integrity else ""
        print(f"{r.condition:<12} {r.runid:<10} {r.model:<8} {s:>7} {g:>7} "
              f"{a1:>7} {r.real_attempts:>5} {r.tune_attempts:>5} {b:>6}  {flag}")

    pooled = {c: [r for r in runs if r.condition == c and r.ok] for c in CONDITIONS}
    excluded = [r for r in runs if not r.ok]

    # --- per-condition ---
    print("\n" + "-" * 78)
    print("PER-CONDITION  (pooled = complete, clean, on-model runs only)")
    print("-" * 78)
    print(f"{'condition':<26} {'n':>2}  {'score (mean+/-sd)':>20}  {'gap (mean+/-sd)':>20}")
    for c, label in CONDITIONS.items():
        rs = pooled[c]
        if not rs:
            print(f"{label:<26} {0:>2}   -- no usable runs --")
            continue
        S = [r.final_score for r in rs]
        G = [r.final_gap for r in rs if r.final_gap is not None]
        sd_s = f"+/-{statistics.stdev(S):.4f}" if len(S) > 1 else "       "
        sd_g = f"+/-{statistics.stdev(G):.2f}" if len(G) > 1 else "      "
        print(f"{label:<26} {len(rs):>2}   {statistics.mean(S):.4f} {sd_s:<9} "
              f"  {statistics.mean(G):+.2f}% {sd_g}")

    # --- how much of the gain happens on attempt 1? ---
    if base_score is not None:
        print("\n" + "-" * 78)
        print("WHERE THE GAIN COMES FROM")
        print("-" * 78)
        print("  If most of the improvement lands on the FIRST attempt, it is recall,")
        print("  not search - and no cross-agent channel could have contributed to it.")
        print(f"{'condition':<26} {'attempt-1':>10} {'final':>8} {'gain@1':>9} {'gain@2-12':>10} {'%@1':>6}")
        for c, label in CONDITIONS.items():
            rs = [r for r in pooled[c] if r.first_score is not None]
            if not rs:
                continue
            a1 = statistics.mean([r.first_score for r in rs])
            fin = statistics.mean([r.final_score for r in rs])
            g1, grest = a1 - base_score, fin - a1
            tot = fin - base_score
            pct = 100 * g1 / tot if tot else float("nan")
            print(f"{label:<26} {a1:>10.4f} {fin:>8.4f} {g1:>+9.4f} {grest:>+10.4f} {pct:>5.0f}%")

    # --- pairwise ---
    print("\n" + "-" * 78)
    print("PAIRWISE  (effect size first; p is structurally limited - see below)")
    print("-" * 78)
    pairs = [("full", "noknowledge"), ("full", "noheartbeat"),
             ("noknowledge", "noheartbeat")]
    for metric, attr, better in (("score", "final_score", "higher"),
                                 ("gap %", "final_gap", "lower")):
        print(f"\n  metric: {metric}  ({better} is better)")
        for x, y in pairs:
            A = [getattr(r, attr) for r in pooled[x] if getattr(r, attr) is not None]
            B = [getattr(r, attr) for r in pooled[y] if getattr(r, attr) is not None]
            if len(A) < 2 or len(B) < 2:
                print(f"    {x:<12} vs {y:<12}  insufficient usable runs")
                continue
            g = hedges_g(A, B)
            _, p = mannwhitney_exact(A, B)
            fl = p_floor(len(A), len(B))
            fmt = "{:+.2f}%" if metric.startswith("gap") else "{:.4f}"
            print(f"    {x:<12} vs {y:<12}  "
                  f"{fmt.format(statistics.mean(A))} vs {fmt.format(statistics.mean(B))}"
                  f"   g={g:+.2f}   exact p={p:.2f}  (floor {fl:.2f})")

    # --- caveats ---
    n = min((len(v) for v in pooled.values() if v), default=0)
    print("\n" + "=" * 78)
    print("INTEGRITY / CAVEATS")
    print("=" * 78)
    if excluded:
        for r in excluded:
            print(f"  EXCLUDED  {r.condition}/{r.runid}: {'; '.join(r.integrity)}")
    else:
        print("  No runs excluded: all are complete, clean, and on the pooled model.")
    if n:
        fl = p_floor(n, n)
        print(f"\n  SIGNIFICANCE FLOOR: with n={n} vs n={n}, the exact two-sided")
        print(f"  Mann-Whitney has only C({2*n},{n})={math.comb(2*n, n)} arrangements, so the smallest")
        print(f"  attainable p is 2/{math.comb(2*n, n)} = {fl:.2f}. p < 0.05 is UNREACHABLE BY")
        print("  CONSTRUCTION at this sample size. A non-significant result here is a")
        print("  statement about the DESIGN, not evidence of no effect. Read the effect")
        print("  sizes and the raw per-run numbers, not the p-values.")


if __name__ == "__main__":
    main()
