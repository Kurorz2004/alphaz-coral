"""Task 3 — score the ablation and audit that each condition actually held.

Final Score of a run = the best real-mode attempt score, i.e. what `coral log`
puts at the top of the leaderboard. Tune attempts are excluded (they are a
cheaper workload and CORAL hides them from the leaderboard by default).

Run:  uv run --project ../coral-upstream python analyze.py
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent

# Every pooled run must share a model. Two Opus agents exhaust the 5-hour API
# quota in under 3 h, so the ablation runs on sonnet. The banked Task 2 run and
# the abandoned Opus attempt are reported as *reference rows*, never pooled.
TARGET_MODEL = "sonnet"

# Same task.yaml, same budget, same 16 cores, vanilla upstream code — but Opus.
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
    model: str = "?"
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
        """Usable as a pooled sample: finished, clean, and on the pooled model."""
        return self.final_score is not None and not self.integrity and self.model == TARGET_MODEL


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


def _model_of(path: Path) -> str:
    """The model that *actually* ran, normalized to the alias vocabulary.

    config.yaml only records the runtime alias (`model: sonnet`); ~/.claude
    settings can remap that alias to another provider (ANTHROPIC_DEFAULT_SONNET_MODEL
    = deepseek-v4-pro is how full-s1/nok-s1 ran on deepseek while their config said
    sonnet). The agent logs carry the real `"model":"..."` string — trust those, and
    fall back to the config label only when no logs exist yet.
    """
    logs = path / ".coral/public/logs"
    counts: dict[str, int] = {}
    for f in logs.glob("*.log"):
        for m in re.findall(r'"model":"([^"]+)"', f.read_text(errors="replace")):
            if m != "<synthetic>":
                counts[m] = counts.get(m, 0) + 1
    if counts:
        real = max(counts, key=counts.get)
        if real.startswith("claude-sonnet"):
            return "sonnet"
        if real.startswith("claude-opus"):
            return "opus"
        if real.startswith("claude-haiku"):
            return "haiku"
        return real  # deepseek-v4-pro, etc. — never matches TARGET_MODEL, so excluded

    cfg = path / ".coral/config.yaml"
    if cfg.is_file():
        for line in cfg.read_text().splitlines():
            s = line.strip()
            if s.startswith("model:"):
                return s.split(":", 1)[1].strip()
    return "?"


def _rate_limited(path: Path) -> bool:
    """Did any agent get an API quota rejection during this run?

    A rate-limited agent exits 1, gets restarted, trips the crash-burst breaker,
    and produces nothing for the rest of the run. Its attempts before the first
    rejection are fine; everything after is an artefact of the quota, not of the
    condition. Any run with a rejection *and* no auto_stop is unusable.
    """
    logs = path / ".coral/public/logs"
    return any('"status":"rejected"' in f.read_text(errors="replace") for f in logs.glob("*.log"))


def _authoritative_real_count(path: Path) -> int | None:
    """CORAL's own real-attempt tally from auto_stop.json.

    This is the number CORAL used to decide `max_real_attempts` was reached, so
    it is immune to verify-race duplicates and failed (score=None) evals that
    leave extra files in the attempts dir. None if the run never auto-stopped.
    """
    f = path / ".coral/public/auto_stop.json"
    if not f.is_file():
        return None
    try:
        return int(json.loads(f.read_text()).get("real_attempt_count"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def load_run(runid: str, condition: str, path: Path) -> Run:
    r = Run(runid=runid, condition=condition, path=path, model=_model_of(path))
    finished = (path / ".coral/public/auto_stop.json").is_file()
    if not finished:
        r.integrity.append("no auto_stop.json — run did not finish its eval budget")
    if _rate_limited(path):
        r.integrity.append(
            "API rate-limit rejection in agent logs"
            + ("" if finished else " — run died on quota, not on the condition")
        )
    if r.model != TARGET_MODEL:
        r.integrity.append(f"model={r.model!r}, not pooled (pooling {TARGET_MODEL!r})")

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

    # Prefer CORAL's own counter over the raw file count: a verify-race can leave
    # an extra failed (score=None) attempt file that CORAL never counted toward
    # its budget. Fall back to scored real attempts when there is no auto_stop.
    authoritative = _authoritative_real_count(path)
    if authoritative is None:
        authoritative = len(scored)
    if authoritative != 12:
        r.integrity.append(f"expected 12 real attempts, found {authoritative}")

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

    # A knowledge dir counts only if it holds actual content. `coral ui` (and the
    # mid-run seed) create bare empty notes/skills dirs that carry no notes or
    # skills — an empty shell is a tooling artifact, not a leak. Require a file.
    def _has_content(d: Path) -> bool:
        return d.is_dir() and any(f.is_file() for f in d.rglob("*"))

    knowledge_dirs = [d for d in ("notes", "skills", "roles", "agents") if _has_content(pub / d)]
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
        # Match CORAL's *seeded* assets by the path they would live at. A bare
        # name like "deep-research" also matches Claude Code's own global skill
        # list, which every arm has and which CORAL does not control.
        for banned in (".claude/skills/", ".claude/notes/", ".claude/roles/", "coral notes", "coral skills"):
            if banned in log_text:
                bad.append(f"agent reached the ablated channel via {banned!r}")
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
        # `latest` is a symlink; `<task-slug>/` is a stray dir CORAL leaves behind
        # when results_dir and run_dir disagree. A run is a dir with a .coral/.
        for run_dir in sorted(p for p in d.iterdir() if p.is_dir() and not p.is_symlink()):
            if (run_dir / ".coral").is_dir():
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
    hdr = f"{'run':<14}{'condition':<14}{'model':<8}{'final':>10}{'real':>6}{'tune':>6}{'fail':>6}{'best@':>7}{'min':>7}"
    print(hdr)
    print("-" * 100)
    for r in runs:
        score = f"{r.final_score:.6f}" if r.final_score is not None else "—"
        wall = f"{r.wall_minutes:.0f}" if r.wall_minutes else "—"
        print(
            f"{r.runid:<14}{r.condition:<14}{r.model:<8}{score:>10}{r.real_attempts:>6}"
            f"{r.tune_attempts:>6}{r.failed_attempts:>6}{str(r.best_at_eval or '—'):>7}{wall:>7}"
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
