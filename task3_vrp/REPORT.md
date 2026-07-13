# Task 3 — Ablation: what happens when you switch off CORAL's knowledge channel

**Headline: a null result, and an honest account of why the experiment could not have
found anything.** Neither ablation degraded performance. Both ablated conditions scored
*nominally better* than full CORAL. The effect, such as it is, is smaller than the
seed-to-seed noise, points the wrong way, and lives inside a window that is mostly
consumed before any cross-agent channel can act.

The result is real. The interesting part is the diagnosis: **CVRP cannot discriminate
this hypothesis**, and the numbers say precisely why.

---

## Design

| | |
|---|---|
| Task | CVRP, 50 hidden instances, n = 100 customers, 10 s/instance |
| Conditions | `full` (control) · **A** `agents.knowledge=false` · **B** `agents.heartbeat=[]` |
| Runs | 3 seeds × 3 conditions = 9 |
| Agents | 2 per run, sonnet, 12 real attempts each (fixed budget, no score threshold) |
| Score | mean over instances of `reference_distance / solver_distance`. Higher better. |

Score is *not* an optimality ratio. The reference is a PyVRP HGS heuristic (unlimited
fleet, best of 3 seeds × 60 s), not a proven optimum, so the score is not capped at 1.0.
Mean gap % is reported alongside it throughout, because score compresses into a narrow
0.95–0.99 band that makes real progress look like nothing.

**Seed baseline (hidden set): 0.9474, mean gap +5.65%.** Every condition starts here.

---

## Results

### Per condition (mean ± sd over 3 seeds)

| Condition | n | Final score | Mean gap |
|---|---|---|---|
| Full CORAL (control) | 3 | **0.9771 ± 0.0056** | +2.37% ± 0.59 |
| **A** — notes/skills disabled | 3 | **0.9819 ± 0.0071** | +1.86% ± 0.74 |
| **B** — heartbeats disabled | 3 | **0.9803 ± 0.0012** | +2.04% ± 0.12 |

### Per run

| Condition | Run | Score | Gap | Attempt-1 score | Best at |
|---|---|---|---|---|---|
| full | full-s1 | 0.9828 | +1.78% | 0.9786 | 12 |
| full | full-s2 | 0.9770 | +2.38% | 0.9586 | 10 |
| full | full-s3 | 0.9716 | +2.96% | 0.9626 | 8 |
| noknowledge | nok-s1 | 0.9805 | +2.01% | 0.9538 | 11 |
| noknowledge | nok-s2 | 0.9896 | +1.06% | 0.9710 | 10 |
| noknowledge | nok-s3 | 0.9757 | +2.52% | 0.9713 | 10 |
| noheartbeat | nohb-s1 | 0.9789 | +2.17% | 0.9610 | 11 |
| noheartbeat | nohb-s2 | 0.9805 | +2.01% | 0.9682 | 11 |
| noheartbeat | nohb-s3 | 0.9814 | +1.93% | 0.9581 | 11 |

All 9 runs completed, all on the pooled model (sonnet), none excluded.

### Pairwise

| Comparison | Score | Hedges' g | Exact p |
|---|---|---|---|
| full vs A | 0.9771 vs 0.9819 | −0.61 | 0.70 |
| full vs B | 0.9771 vs 0.9803 | −0.62 | 0.70 |
| A vs B | 0.9819 vs 0.9803 | +0.26 | 1.00 |

Negative *g* = the ablated arm scored **higher**. The same statistics on mean gap % give
the identical picture (g = +0.61 / +0.63 / −0.26; gap is inverted, so the sign flips).

---

## What I observe

### 1. Removing the knowledge channel did not hurt. It nominally helped.

Both ablations beat the control. `p = 0.70` is not "underpowered but suggestive" — it is
about as consistent with *no effect* as data can be. The direction being wrong is itself
informative: a masked-but-real positive effect would not systematically invert.

### 2. Seed noise is ~3× the size of the condition effect.

| | Spread |
|---|---|
| **Within** one condition (noknowledge) | 0.0139 |
| **Within** one condition (control) | 0.0112 |
| **Between** the three condition means | **0.0048** |

Re-running the *same* condition with a different seed moves the score more than changing
the condition does. This is the single most important number in the study, and it is only
visible because each condition was run 3 times.

**Had each condition been run once**, across all 9 possible single-seed pairings the
control "beats" condition A in **3 of 9** draws, with the measured difference ranging from
**−0.0180 to +0.0071** depending purely on which seeds were drawn. A one-run-per-condition
experiment would have produced a confident result in *either* direction, at up to 4× the
true magnitude. The replication is what prevents that.

### 3. Roughly half the total gain lands on attempt 1 — before any channel can act.

| Condition | Attempt-1 | Final | Gain @1 | Gain @2–12 | % on attempt 1 |
|---|---|---|---|---|---|
| Full CORAL | 0.9666 | 0.9771 | +0.0192 | +0.0105 | **65%** |
| A — no notes/skills | 0.9654 | 0.9819 | +0.0180 | +0.0165 | **52%** |
| B — no heartbeats | 0.9624 | 0.9803 | +0.0150 | +0.0178 | **46%** |

The agents *recall* the textbook CVRP recipe — Clarke-Wright → Prins split → giant-tour
ILS — and write it down on the first attempt. One attempt title says it outright:
*"Prins split + giant-tour ILS + sweep + Or-opt."* That knowledge is in the model's
weights before the run begins, so no amount of note-sharing can add to it.

(Genuine iterative improvement *does* continue afterwards: +0.010 to +0.018 over the
remaining 11 attempts. So this is not pure recall — but it halves the window in which the
mechanism could possibly show up.)

### 4. The experiment has almost no dynamic range. That is the actual finding.

Stacking the numbers:

| | |
|---|---|
| Seed baseline | 0.9474 |
| Best any condition reaches | ~0.98 |
| Total available gain | **~0.033** |
| Consumed by attempt-1 recall | ~half |
| Searchable window left for the mechanism | **~0.015** |
| Seed-to-seed noise | **±0.006** |

You are hunting an effect inside a ~0.015 window with a ±0.006 measurement, at n = 3.
There was never enough resolution to detect anything.

**So the correct reading is not "CORAL's knowledge channel does nothing." It is "this task
cannot answer the question."** A knowledge-sharing channel can only pay off if there is
knowledge to accumulate. When both agents already know the answer, deleting the notes
costs nothing — you have built a channel and measured it on a route with no traffic.

### 5. n = 3 cannot reach significance, by construction.

Exact two-sided Mann-Whitney p-floor by sample size:

| n per condition | 3 | 4 | 5 | 6 |
|---|---|---|---|---|
| smallest attainable p | **0.100** | 0.029 | 0.008 | 0.002 |

With 3 vs 3 there are only C(6,3) = 20 arrangements, so **p < 0.05 is unreachable no matter
how large the effect is**. `analyze.py` prints this next to every p-value so a null is never
misread as evidence of absence. The assessment asks for ≥3 runs; 3 is the minimum that
reveals noise, and one short of the minimum that permits significance.

Power, at the observed pooled sd of 0.0064: detecting a **+0.010** effect (≈ a third of all
available gain) needs **~7 seeds/condition**; detecting the **+0.0048** actually observed
needs **~29**.

---

## Anti-gaming: the dataset had to be rebuilt first

The task originally used **CVRPLIB Set X**, which is trivially cheatable and would have
invalidated the whole ablation:

- `dimension` is a **unique key** across all 100 X instances (verified: 100/100 distinct)
  and is the **first argument to `solve()`**.
- The optimal **routes** are published (CVRPLIB `.sol`, the PyVRP/Instances GitHub repo).
- CORAL enables web access by default (`agents.research` defaults `True`; `Bash` is allowed
  unconditionally, so denying `WebFetch` does not block `curl`).

A five-line `{101: [...routes...]}` lookup scores ~1.0 without solving anything. Renaming
instances does not help — the agent never sees the name; `dimension` alone identifies them.

Worse for *this* experiment specifically: a cheat discovered by one agent and shared through
notes would propagate **in the sharing-enabled arm only**, inflating exactly the condition
under test. Contamination would have masqueraded as "knowledge sharing works."

**Fix:** instances are generated fresh from the XML100 generator with private seeds, so no
optimum for them has ever been published. See `../HANDOFF.md` and `generate_taskdata.py`.

### Reference quality, measured not assumed

The reference is HGS, not an optimum — so its error was measured against frozen XML100
instances whose optima *are* proven (same generator, same distribution), 420 runs:

| HGS budget | % exactly optimal | mean gap | worst gap |
|---|---|---|---|
| 10 s | 26.7% | 0.28% | 1.15% |
| 30 s | 56.7% | 0.11% | 0.62% |
| best-of-3 × 30 s | 66.7% | **0.068%** | 0.62% |

HGS does **not** reliably hit the optimum — it misses ~1/3 of the time even at 30 s. But it
misses *small*. And because the reference is a **fixed per-instance constant shared by every
condition**, `score_A / score_B` is exactly invariant to that error: it shifts the absolute
score by ~0.1%, and cannot bias the between-condition comparison. Evidence: `labelval/`.

Two incidental findings from that validation:
- **91 of the 10,000 published XML100 `.sol` files are malformed** (a customer visited
  twice; e.g. `XML100_1121_04` has customer 33 in both Route #5 and #23). Excluded.
- `k = ceil(total_demand/capacity)` is **not** the optimal fleet size — the true optimum
  needs more routes 11.8% of the time (up to +10). So the fleet is left non-binding.

---

## Conditions verified to have actually held

Stock CORAL silently *regrows* disabled heartbeats (HANDOFF defect #5, two paths). Runs
used the `task3-ablation` fork with both fixes. Verified from run artefacts, not config:

| | Full (control) | Ablated |
|---|---|---|
| **A** notes / skills | 5 notes, 4 skills | **0 / 0** |
| **B** heartbeat actions | `reflect` (every 1), `consolidate` (every 10) | **`{"actions": []}`** |

---

## Recommendation for Task 4

Do not buy more seeds on this task — the effect is ~zero and pointing the wrong way.
Buy **dynamic range**.

The most surgical change: cut `time_limit` from 10 s to **1–2 s**. That moves the bottleneck
from *which algorithm* (recalled instantly, identical across conditions) to *how fast can you
make it* — profiling, numpy vectorisation, neighbour-list pruning, move-evaluation caching.
That craft is genuinely **accumulable** across attempts and across agents, which is exactly
the traffic the notes channel is supposed to carry. Budget **5–7 seeds/condition**, so that
significance is reachable and a meaningful effect is detectable.

---

## Files

| Path | Purpose |
|---|---|
| `task.yaml` | Task definition (2 agents, 12 real attempts, no score threshold) |
| `grader/` | CVRP grader — feasibility + EUC_2D scoring |
| `seed/` | Seed repo the agents start from (CW + 2-opt + ILS, 0.9474) |
| `taskdata/` | 50 hidden instances + frozen HGS reference values |
| `seed_baseline.json` | Seed solver's score on the hidden set — the floor every condition inherits |
| `generate_taskdata.py` | Instance generation + HGS labelling + validation |
| `analyze.py` | This report's numbers (`python analyze.py`) |
| `labelval/` | The 420-run evidence that the HGS reference is trustworthy |
| `run_ablation.sh` | Runs the 9 experiments |

## Reproducing

```bash
python analyze.py                 # numbers in this report, from results/
./run_ablation.sh                 # re-run the 9 experiments (long)
```

`taskdata/` is committed on purpose. HGS labelling is wall-clock bounded, so regenerating
shifts the reference values — every condition must divide by the *same* denominator or the
conditions stop being comparable. **Do not re-run `generate_taskdata.py`** against an
existing results set.
