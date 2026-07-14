---
creator: captain-ahab
created: 2026-07-10T00:10:00
posture: engineer
lane: nowicki-smutnicki tabu search engine (N5 + Taillard O(1) move estimate + incremental head/tail)
budget: 6 evals
abandon_if: after 4 real evals the TS engine cannot beat the 0.7038 tabu reference on the hidden set, AND local 100x100 iteration throughput stays under 2k accepted moves in 10s (i.e. Python is the binding constraint, not the algorithm)
---
# Focus: tabu-engine

## Environment facts established (verified, 2026-07-10)
- **No C compiler** (`gcc`/`cc`/`clang` absent), **no numba, no Cython, no scipy**. numpy 2.5.1 only. Python 3.13.
  => Any speed must come from tight CPython + algorithmic incrementality. Do not plan around a native extension.
- 16 cores visible. `multiprocessing` (stdlib) is an unexploited ~10x compute lever, untested.
- Grader `wall_timeout = 3*time_limit + 60`, but `time_limit` is the advertised honest budget.
  I will respect `time_limit` (with ~8% safety margin), not the wall timeout.
- Module import time is NOT counted against `time_limit` (grader starts the clock after `exec_module`).

## Why this has positive EV
The stated reference ladder tops out at "tabu search (20s/inst) = 0.7038". To beat it we need
*more iterations per second*, not a cleverer neighbourhood. At 10,000 ops a full O(n) makespan
recompute is ~10ms in CPython => only ~1000 moves in 10s, far below the ~1e5 that TS needs.

So the whole investigation is about one number: **accepted moves per second at 100x100**.
Two multiplicative levers:
1. Taillard's O(1) lower-bound estimate for move *selection* (no recompute per candidate).
2. Worklist-based *incremental* head/tail repair after an accepted move (touch only changed nodes).

## What I'll publish
- `solution.py` with a real TSAB-style engine.
- A note with the measured moves/sec at each of 20x20 / 50x50 / 100x100 — the number that tells
  the team whether Python is the binding constraint. This is the fact everything else depends on.

## What this leaves open for teammates
Construction heuristics (GT variants, shifting bottleneck), LNS / machine-resequencing,
multiprocessing parallel restarts, and *falsifying* my throughput claims. If you're picking a lane,
those are all uncontested.
