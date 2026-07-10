"""Task 3 — score the ablation and audit that each condition actually held.

Final Score of a run = the best real-mode attempt score, i.e. what `coral log`
puts at the top of the leaderboard. Tune attempts are excluded (they are a
cheaper workload and CORAL hides them from the leaderboard by default).

Run:  uv run --project ../coral-upstream python analyze.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent

# The banked Task 2 run is full-CORAL sample #1: same task.yaml, same budget,
# same 16 cores, vanilla upstream code. The `agents.knowledge` commit is proven
# byte-identical for knowledge=True (tests/test_knowledge_ablation.py), so runs
# on the fork's control arm are poolable with it.
BANKED_FULL = HERE.parent / "task2/results/job-shop-scheduling/2026-07-09_235518"

CONDITIONS = {
    "full": "Full CORAL (control)",
    "noknowledge": "A — notes/skills disabled",
    "noheartbeat": "B — heartbeats disabled",
}


@dataclass
class Run:
    runid: str
    condition: str
    path: Path
    final_score: float | None = None
    real_attempts: int = 0
    tune_attempts: int = 0
    failed_attempts: int = 0
    best_at_eval: int | None = None
    wall_minutes: float | None = None
    agents: dict[str, int] = field(default_factory=dict)
    trajectory: list[float] = field(default_factory=list)
    integrity: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.final_score is not None and not self.integrity


def _attempts(run: Path) -> list[dict]:
    d = run / ".coral/public/attempts"
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    out.sort(key=lambda a: a.get("timestamp", ""))
    return out


def _budget(a: dict) -> str:
    return (a.get("metadata") or {}).get("budget_class", "real")


def load_run(runid: str, condition: str, path: Path) -> Run:
    r = Run(runid=runid, condition=condition, path=path)
    if not (path / ".coral/public/auto_stop.json").is_file():
        r.integrity.append("no auto_stop.json — run did not finish its eval budget")

    atts = _attempts(path)
    if not atts:
        r.integrity.append("no attempts found")
        return r

    reals = [a for a in atts if _budget(a) == "real"]
    r.real_attempts = len(reals)
    r.tune_attempts = sum(1 for a in atts if _budget(a) == "tune")
    r.failed_attempts = sum(1 for a in reals if a.get("score") is None)
    for a in reals:
        r.agents[a["agent_id"]] = r.agents.get(a["agent_id"], 0) + 1

    scored = [a for a in reals if a.get("score") is not None]
    if scored:
        best = max(scored, key=lambda a: a["score"])
        r.final_score = best["score"]
        r.best_at_eval = scored.index(best) + 1
        run_best = -math.inf
        for a in scored:
            run_best = max(run_best, a["score"])
            r.trajectory.append(run_best)

    ts = [datetime.fromisoformat(a["timestamp"]) for a in atts if a.get("timestamp")]
    if len(ts) >= 2:
        r.wall_minutes = (max(ts) - min(ts)).total_seconds() / 60

    if r.real_attempts != 12:
        r.integrity.append(f"expected 12 real attempts, found {r.real_attempts}")

    r.integrity.extend(_audit_condition(path, condition))
    return r


def _audit_condition(path: Path, condition: str) -> list[str]:
    """Verify from the run's own artifacts that the condition held end-to-end.

    A config flag proves intent, not effect. An agent can `mkdir` a notes
    directory the harness never created, and `coral heartbeat set` can re-register
    an action the config dropped. So the ablations are checked against what the
    run actually produced.
    """
    bad: list[str] = []
    pub = path / ".coral/public"
    cfg = (path / ".coral/config.yaml").read_text() if (path / ".coral/config.yaml").is_file() else ""
    logs = sorted((pub / "logs").glob("*.log"))
    log_text = "\n".join(f.read_text(errors="replace") for f in logs)

    knowledge_dirs = [d for d in ("notes", "skills", "roles", "agents") if (pub / d).exists()]
    # `## Heartbeat:` heads every injected heartbeat prompt; `## Eval #N Results`
    # heads the score report that rides along with it (manager.py builds them
    # together, which is why B loses both).
    heartbeats_fired = log_text.count("## Heartbeat:")
    headers_seen = log_text.count("## Eval #")

    if condition == "full":
        if "knowledge: false" in cfg:
            bad.append("control run has knowledge=false")
        if not knowledge_dirs:
            bad.append("control run has no knowledge dirs")
        if heartbeats_fired == 0:
            bad.append("control run: no heartbeat ever fired")
    elif condition == "noknowledge":
        if "knowledge: false" not in cfg:
            bad.append("config does not record knowledge=false")
        if knowledge_dirs:
            bad.append(f"knowledge dirs present despite ablation: {knowledge_dirs}")
        for banned in ("create-notes", "deep-research", "librarian"):
            if banned in log_text:
                bad.append(f"agent referenced ablated asset {banned!r}")
        if heartbeats_fired == 0:
            bad.append("no heartbeat fired (reflect/pivot should survive Condition A)")
        if "Knowledge Synthesis" in log_text or "Wiki Lint" in log_text:
            bad.append("a note-writing heartbeat fired despite ablation")
    elif condition == "noheartbeat":
        if heartbeats_fired:
            bad.append(f"{heartbeats_fired} heartbeat prompt(s) fired despite ablation")
        if headers_seen:
            bad.append(f"{headers_seen} eval header(s) injected despite ablation")
        for f in (pub / "heartbeat").glob("*.json"):
            if '"name"' in f.read_text():
                bad.append(f"heartbeat actions registered in {f.name}")
    return bad


def discover() -> list[Run]:
    runs: list[Run] = []
    if BANKED_FULL.is_dir():
        runs.append(load_run("task2-banked", "full", BANKED_FULL))
    for cond in CONDITIONS:
        d = HERE / "results" / cond
        if not d.is_dir():
            continue
        for run_dir in sorted(p for p in d.iterdir() if p.is_dir() and p.name != "latest"):
            runs.append(load_run(run_dir.name, cond, run_dir))
    return runs


# --- statistics -------------------------------------------------------------
# n=3 per arm. A t-test's p-value would be theatre. Report the descriptives, an
# effect size, and the exact rank test, whose best possible one-sided p at
# n=3 vs 3 is 1/20 = 0.05 — reached only under complete separation.


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def hedges_g(a: list[float], b: list[float]) -> float:
    """Bias-corrected standardised mean difference (a - b)."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp = math.sqrt(((na - 1) * stdev(a) ** 2 + (nb - 1) * stdev(b) ** 2) / (na + nb - 2))
    if sp == 0:
        return float("inf") if mean(a) != mean(b) else 0.0
    d = (mean(a) - mean(b)) / sp
    j = 1 - 3 / (4 * (na + nb) - 9)
    return d * j


def mannwhitney_exact(a: list[float], b: list[float]) -> tuple[float, float]:
    """Exact two-sided Mann-Whitney U p-value by enumeration. Returns (U, p)."""
    na, nb = len(a), len(b)
    pooled = sorted(a + b)
    n = na + nb

    def u_of(idx: tuple[int, ...]) -> float:
        ga = [pooled[i] for i in idx]
        gb = [pooled[i] for i in range(n) if i not in idx]
        u = sum((x > y) + 0.5 * (x == y) for x in ga for y in gb)
        return u

    observed = sum((x > y) + 0.5 * (x == y) for x in a for y in b)
    stat = min(observed, na * nb - observed)
    all_u = [u_of(c) for c in combinations(range(n), na)]
    extreme = sum(1 for u in all_u if min(u, na * nb - u) <= stat)
    return observed, extreme / len(all_u)


def main() -> None:
    runs = discover()
    if not runs:
        print("No runs found. Run ./run_ablation.sh first.")
        return

    print("=" * 100)
    print("PER-RUN")
    print("=" * 100)
    hdr = f"{'run':<14}{'condition':<14}{'final':>10}{'real':>6}{'tune':>6}{'fail':>6}{'best@':>7}{'min':>7}  agents"
    print(hdr)
    print("-" * 100)
    for r in runs:
        score = f"{r.final_score:.6f}" if r.final_score is not None else "—"
        wall = f"{r.wall_minutes:.0f}" if r.wall_minutes else "—"
        agents = ",".join(f"{k}:{v}" for k, v in sorted(r.agents.items()))
        print(
            f"{r.runid:<14}{r.condition:<14}{score:>10}{r.real_attempts:>6}"
            f"{r.tune_attempts:>6}{r.failed_attempts:>6}{str(r.best_at_eval or '—'):>7}{wall:>7}  {agents}"
        )
        for msg in r.integrity:
            print(f"{'':>14}!! {msg}")

    usable = {c: [r for r in runs if r.condition == c and r.ok] for c in CONDITIONS}
    excluded = [r for r in runs if not r.ok]
    if excluded:
        print(f"\n{len(excluded)} run(s) EXCLUDED from the statistics (integrity failures above).")

    print()
    print("=" * 100)
    print("FINAL SCORE — mean ± std (sample sd, ddof=1)")
    print("=" * 100)
    print(f"{'condition':<32}{'n':>3}{'mean':>12}{'sd':>11}{'min':>11}{'max':>11}   runs")
    print("-" * 100)
    stats = {}
    for cond, label in CONDITIONS.items():
        xs = [r.final_score for r in usable[cond]]
        if not xs:
            print(f"{label:<32}{0:>3}{'—':>12}")
            continue
        stats[cond] = xs
        sd = stdev(xs)
        sd_s = f"{sd:.6f}" if not math.isnan(sd) else "—"
        vals = " ".join(f"{x:.4f}" for x in xs)
        print(
            f"{label:<32}{len(xs):>3}{mean(xs):>12.6f}{sd_s:>11}"
            f"{min(xs):>11.6f}{max(xs):>11.6f}   {vals}"
        )

    if "full" in stats:
        base = stats["full"]
        print()
        print("=" * 100)
        print("VS FULL CORAL")
        print("=" * 100)
        print(f"{'condition':<32}{'Δ mean':>11}{'Δ %':>9}{'Hedges g':>11}{'U':>7}{'exact p':>10}")
        print("-" * 100)
        for cond in ("noknowledge", "noheartbeat"):
            xs = stats.get(cond)
            if not xs:
                continue
            d = mean(xs) - mean(base)
            u, p = mannwhitney_exact(xs, base)
            print(
                f"{CONDITIONS[cond]:<32}{d:>+11.6f}{100 * d / mean(base):>+9.2f}"
                f"{hedges_g(xs, base):>11.2f}{u:>7.1f}{p:>10.3f}"
            )
        print()
        print("With n=3 per arm the smallest attainable two-sided exact p is 0.10")
        print("(one-sided 0.05), and only under complete separation of the two groups.")
        print("Read the effect size and the raw scores; treat p as a tiebreak, not a verdict.")

    out = HERE / "results/summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "runid": r.runid,
                        "condition": r.condition,
                        "final_score": r.final_score,
                        "real_attempts": r.real_attempts,
                        "tune_attempts": r.tune_attempts,
                        "failed_attempts": r.failed_attempts,
                        "best_at_eval": r.best_at_eval,
                        "wall_minutes": r.wall_minutes,
                        "agents": r.agents,
                        "trajectory": r.trajectory,
                        "integrity": r.integrity,
                        "usable": r.ok,
                    }
                    for r in runs
                ],
                "by_condition": {
                    c: {"n": len(v), "mean": mean(v), "sd": stdev(v), "scores": v}
                    for c, v in stats.items()
                },
            },
            indent=2,
        )
    )
    print(f"\nwrote {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
