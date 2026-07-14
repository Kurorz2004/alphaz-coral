---
creator: captain-ahab
created: 2026-07-09T20:05:00+00:00
commit: 9166b82a8dac
type: experiment
claim: "Tails only rank moves -- they never affect correctness -- so refreshing them every 3rd super-iteration buys ~20% more super-iterations and beats fresh tails in every rep; and the grader's lower bound is loose by 8.5-20%, size-dependently, so the reported gap overstates distance from optimality."
status: confirmed
confidence: high
evidence:
  attempt: 9166b82a8dac
  score_delta: "0.7147 -> 0.7171 (+0.0024)"
  verified: true
based_on: [93a06cb9685b, 02cc680d2d5b, 552950a26894]
touched: [solution.py, .claude/skills/jssp-calibrate/scripts/strong_lb.py]
tags: [tabu-search, taillard-bound, throughput, lower-bound, jackson-preemptive, saturation]
---

# Lazy tails: +0.0024 by computing 2/3 fewer of them — and the grader's bound is loose by 8.5-20%

## Context

Real mode, hidden set, 10 s/instance. Two contributions, one code and one measurement.
Follows [eval-7](eval-7-silent-parallelism-and-kahn-bookkeeping.md), which cut the Kahn
preamble; that made tails the single largest remaining cost in a super-iteration.

## Result

| | eval 7 `02cc680d` | eval 8 `93a06cb9` | eval 9 `9166b82a` |
|---|---|---|---|
| **hidden score** | 0.7150 | 0.7147 | **0.7171** |
| hidden mean gap vs LB | 40.26% | 40.29% | 39.78% |
| hidden 100x100 | 8566 / 8627 / 8709 | 8532 / 8627 / 8687 | **8496 / 8559 / 8621** |
| local 15 s score | — | 0.7295 | 0.7324 |
| 100x100 super-iteration | 6.13 ms | 4.23 ms | ~3.1 ms |

**score: 0.7171.** Note eval 8 (`93a06cb9`, the Kahn fix, a verified 1.35x throughput win) scored
0.7147 versus 0.7150 — a *regression* of 0.0003. It was noise. The hidden score's run-to-run
noise is roughly ±0.002; I now refuse to read any single-eval delta smaller than that.

### Lazy tails: T = refresh interval, 4 large visible instances, 3 reps each

| T | mean ratio | individual runs |
|---|---|---|
| 1 (fresh) | 0.68030 | .67845 / .68005 / .68240 |
| 2 | 0.68441 | .68228 / .68505 / .68590 |
| **3** | **0.68589** | .68518 / .68600 / .68650 |
| 4 | 0.68509 | |
| 6 | 0.68241 | |
| 10 | 0.68505 | |

T=3 beat T=1 in **every rep**, with non-overlapping ranges. That is what distinguishes this from
the KCAP sweep in eval 8, where repeating one config gave 0.66589 then 0.66435.

### The grader's lower bound is loose (`scripts/strong_lb.py`, new)

| instance | grader LB | strong LB | lift | optimum | strongLB/opt |
|---|---|---|---|---|---|
| train_020x020_a | 1245 | 1497 | +20.2% | — | — |
| train_100x100_a | 5721 | 6205 | +8.5% | — | — |
| ft10 | 655 | 808 | +23.4% | 930 | 86.9% |
| orb01 | 695 | 929 | +33.7% | 1059 | 87.7% |
| ta01 | 977 | 1168 | +19.5% | 1231 | 94.9% |
| la26 | 1218 | 1218 | +0.0% | 1218 | 100.0% |

Validated on all 10 published optima: never exceeds one, averages ~93% of optimum
(the grader's bound averages 75-80%).

### 100x100 saturation (single chain, `train_100x100_a`)

| budget | 9 s | 30 s | 90 s | 300 s |
|---|---|---|---|---|
| gap vs grader LB | 50.45% | 47.18% | 46.57% | 45.87% |
| super-iterations | 1,404 | 4,601 | 13,368 | 45,211 |

**33x compute buys 4.6 gap points.**

## Mechanism

- **Tails are a ranking device, not a correctness device.** `t[]` feeds exactly one thing:
  Taillard's O(1) lower bound used to *rank* candidate swaps. The makespan comes from
  `max(h[last op of job j] + dur)`, the critical path from heads alone, and feasibility from the
  heads of the final machine ordering. So stale tails can only mis-rank a move; they cannot
  produce a wrong makespan or an infeasible schedule. Refreshing every 3rd super-iteration trades
  a little selection accuracy for ~20% more super-iterations, and the trade is strongly positive.
  The general principle, which I did not have before: **separate the quantities your algorithm
  needs for *correctness* from the ones it needs for *heuristic guidance*, and let the second
  class go stale.**
- **Why the one-machine bound is so much tighter.** `max(load, chain)` ignores that an operation
  cannot start before its job prefix has run nor finish later than its job suffix allows. Give
  machine m's operations heads `r_j` and tails `q_j` from the job chains, relax every other
  machine, and solve `1|r_j,q_j,pmtn|Cmax` exactly with Jackson's Preemptive Schedule (O(k log k)).
  Preemption only helps, so JPS(m) lower-bounds the JSSP makespan; take the max over machines.
- **The looseness is size-dependent**, which is the part that matters: +20.2% at 20x20 versus
  +8.5% at 100x100. So the grader's gap *flatters* the large instances relative to the small ones,
  and the apparent "the score lives at 100x100" conclusion is *understated*, not overstated:
  our 20x20 result is closer to its true optimum than its 30% gap suggests.

## What did not work

Four ideas falsified locally this round, **zero evals spent**:

- **Batch-size annealing** (shrink kmax toward 1 or 2 as time runs out): 0.6789 (→1) and 0.6806
  (→2) versus 0.6817 fixed. The intuition "coarse early, fine late" is wrong here; the batch is
  not a step size.
- **Randomised multi-start construction.** Best-of-16 non-delay improves the *start* by 1.5% at
  100x100 (9218 → 9080) and 4.6% at 50x50, but paying 1.2-2.4 s of search time for it loses:
  0.6614 (best-of-8) / 0.6618 (best-of-16) versus 0.6654 baseline. **A 1.5% better start does not
  survive the descent.** This also corrects an inference I made in eval 2: I concluded from
  GT-active (+73%) vs non-delay (+61%) that "the start matters a lot." It does not — a *12-point*
  start difference matters; a 1.5-point one is worth less than the search time it costs.
- **Machine-reoptimisation LNS** (eval 3): 713 reopts, 6 improvements. Do not rebuild.
- **Only-improving batches / rollback-on-regression** (eval 7): 0.662 / 0.663 vs 0.683.

## Surprises / open questions

- **I nearly shipped a KCAP "win" that was noise, and I nearly discarded the Kahn fix as a
  regression that was also noise.** Both were ±0.002 events. The lazy-tails result is credible
  precisely because I ran 3 reps and the ranges did not overlap. Rep-before-believe is now the
  rule; a single eval delta under ~0.002 on this objective carries no information.
- **Compute is exhausted at 100x100 and I can prove it.** 33x → 4.6 points. Combined with the
  seed-spread measurement (32 makespan units across 8 seeds), the search is neither basin-limited
  nor restart-limited: it is *rate*-limited, and the rate is CPython's ~0.3 us/node for the
  sequential Kahn drain, which I do not think can be moved without a compiler.
- Open: **the 100x100 optimum is still unknown.** Strong LB = 6205; our best is 8496. On
  benchmarks strong LB averages 93% of optimum, but that ratio is measured on 10x10-20x15
  instances and there is no reason it transfers to 100x100 square. If it did, the optimum would be
  ~6670 and we would be 27% above it — a lot. I do not believe the extrapolation, and I am flagging
  it rather than acting on it.
- Open: one of the three hidden 50x50 instances is persistently ~7 points worse than the other two
  (44.1% vs 37.1% / 37.2%), and the same is true of `train_050x050_b` locally (46.2% vs 36.5%).
  Against the strong LB the difference shrinks but survives (+30.7% vs +21.5%). Unexplained.

## Next

Descending expected payoff.

1. **Cooperative parallel search at 100x100 ("go with the winners").** The one compute lever not
   yet honestly tested. Independent best-of-8 restarts are worthless there (spread 32), but that
   is an argument *for* synchronising: fork W long-lived workers, every ~1.5 s have all of them
   adopt the global-best machine ordering and continue with different tabu state. 6 sync points x
   8 branches. Expected: unclear, possibly 1-2 gap points; this is the honest reason to run it.
   Risk: transfer cost (~20k ints per worker per round) and the possibility that short-horizon
   spread is as small as long-horizon spread — in which case it is worth nothing and I will say so.
2. **N7 / insertion moves.** Still the only untested neighbourhood. The batching evidence
   ("move count beats move quality") argues against it, which is why it deserves one honest test
   rather than continued assumption. Expected: low. Risk: acyclicity conditions are fiddly.
3. **Explain the hard 50x50 instance.** If the search has a systematic weakness when the machine-
   load bound binds, that is worth more than another 1% of throughput.
4. **Do not** tune KCAP, KDIV, STAGB, or anything against 20x20. All are inside the noise floor.

## References

- attempt `9166b82a` (this): lazy tails, `strong_lb.py`, saturation study.
- attempt `93a06cb9`: Kahn bookkeeping, 1.35x super-iterations — scored −0.0003 and was *not* a
  regression. Evidence that the noise floor is ~±0.002.
- attempt `02cc680d`: `Process(fork)` parallelism fix.
- prior note: [eval-7-silent-parallelism-and-kahn-bookkeeping.md](eval-7-silent-parallelism-and-kahn-bookkeeping.md)
- prior note: [eval-3-batched-critical-block-swaps.md](eval-3-batched-critical-block-swaps.md)
- prior note: [eval-1-tabu-engine-and-optimality-calibration.md](eval-1-tabu-engine-and-optimality-calibration.md)
  — the 20x20 saturation study this one mirrors at 100x100.
- infra note: [grader-multiprocessing-pickling.md](../infra/grader-multiprocessing-pickling.md)
- skill: `jssp-calibrate` — now ships **two** tools; `strong_lb.py` is the new one and it changes
  how every gap number on this objective should be read.
- Carlier, J. (1982); Jackson, J.R. (1955) — the one-machine relaxation and the preemptive schedule.
- Taillard, E. (1994) — the O(1) move bound whose *only* consumer is move ranking.
