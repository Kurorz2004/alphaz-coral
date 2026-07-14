---
creator: captain-nemo
created: 2026-07-09T17:50:00+00:00
updated: 2026-07-09T18:42:00+00:00
posture: performance engineer turned structural engineer
lane: large-instance (100x100) scale — CLOSED, premise falsified
budget: 4 evals
abandon_if: "after 3 real evals of machine-reinsertion LNS, 100x100 makespan has not beaten the tabu-only baseline of ~8720 by at least 2%"
status: CLOSED — abandon criterion fired on the first probe, before spending an eval
---
# Focus: beating the flat tabu curve at N = 10,000 — CLOSED

## Outcome: the premise was wrong, and I killed it cheaply

This note claimed that machine-reinsertion LNS was "the only lever I see that can
beat the flat tabu curve at N=10000." **It is not a lever at all.**

A 40-line probe (`lns_probe.py`) settled it before I spent a single eval:
**5 accepted reinsertions out of 1813**; 30s of sweeps moved 9218 → 9210 while
plain tabu reached 8590 in 9s. The diagnostic that made it conclusive rather than
merely disappointing: Schrage's re-sequencing changes ~10 of 100 positions on
99/100 machines, and the **median Δcmax is exactly 0** (best −2, worst +94). The
move is near-neutral by construction, not mis-implemented. captain-ahab reached
the identical conclusion independently (`552950a2`, 6/713).

I also pre-registered a debt in this note — "I owe the team a falsification of my
own `opt/LB ~ 1.30` extrapolation, since it decides where everyone spends their
evals." **That debt is still unpaid**, and it is now the most valuable open item on
the board. See [_open-questions.md](../_open-questions.md) item A.

## What I actually shipped from this lane

- The falsifying experiment (`lns_probe.py`), kept in the repo.
- Two settled negatives that stop the team re-running dead experiments: machine-LNS
  and multi-core restarts (16 parallel @9s: best 8742, versus one 144s run: 8245 —
  breadth is worthless, depth is everything).
- The lever that actually paid, found *after* the LNS failure redirected me:
  N7 block insertion, size-gated (`6bf73ca2`, 0.7188, leaderboard #1).
- The synthesis that explains all of it:
  [_synthesis/cost-model-inversion.md](../_synthesis/cost-model-inversion.md).

## The honest lesson

Both levers I ranked #1 and #3 in eval-2's "descending expected payoff" list
(machine-LNS, multiprocessing) turned out **negative**. The one I ranked #4 (N7)
was the winner. My prior ranking of untested levers is not reliable — but a cheap
falsifying probe costs ~20 minutes and is. I should probe before I rank, and I
should never spend an eval on a structural idea I have not first tried to kill in a
scratch script.

## Successor

New lane: [focus-captain-nemo-headroom-and-idle-budget.md](focus-captain-nemo-headroom-and-idle-budget.md).
