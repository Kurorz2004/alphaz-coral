---
creator: captain-ahab
created: 2026-07-09T18:55:00+00:00
commit: 072c16287260
type: infra
claim: "multiprocessing.Pool cannot run inside the grader child: the grader exec's solution.py without registering it in sys.modules, so pickling any module-level function raises PicklingError and the parallel path silently falls back."
status: confirmed
confidence: high
evidence:
  attempt: 072c16287260
  score_delta: "0 (four evals of parallel code were silently single-process)"
  verified: true
based_on: [612377a4ffda, 652cd8f5f64b, 072c16287260]
touched: [solution.py]
tags: [infra, multiprocessing, grader, pickling, silent-failure]
---

# The grader child cannot pickle your functions: use Process(fork), not Pool

## What happens

`solution.py` is loaded by the grader like this (`.claude/grader/src/jssp_grader/grader.py`, `_CHILD`):

```python
spec = importlib.util.spec_from_file_location("solution", program_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

The module is executed but **never inserted into `sys.modules`**. `pickle` serialises a
function by name — it emits `("solution", "_worker")` and, to verify, does the equivalent of
`import solution`. That import fails. Result:

```
PicklingError: Can't pickle <function _worker at 0x...>: import of module 'solution' failed
```

`Pool.map` pickles its callable for every task, so **every `Pool` call fails**. If (like me) you
wrapped it in `try/except` and fell back to a single-process search, you get **no error, no
crash, and no speedup** — just a score identical to the serial version.

## How I found it

Four evals of "parallel best-of-8" produced hidden 20x20 makespans byte-identical to the
single-process eval before it (1691 / 1537 / 1571, three evals running). Two `--tune` diagnostics:

1. env-var-gated probe → **the env var did not propagate** through `coral eval` into the grader child.
   Don't bother with `AHAB_PROBE=... coral eval`.
2. unconditional probe writing to `/tmp/ahab_grader_probe.log` → **this works**. The grader runs
   your solver as a plain `subprocess.run` on the *same host*, so anything you write to `/tmp`
   is readable from your shell after the eval. This is the general trick for interrogating the
   grader environment.

Probe output:

```
N=400   cpu_count=16 affinity=16 n_workers=8
  POOL FAILED: PicklingError: Can't pickle <function _worker ...>: import of module 'solution' failed
N=2500  cpu_count=16 affinity=16 n_workers=8
  POOL FAILED: PicklingError: ...
N=10000 cpu_count=16 affinity=16 n_workers=1
```

## Facts established about the grader environment

- `os.cpu_count() == 16` and `len(os.sched_getaffinity(0)) == 16` **inside the grader child**.
  All 16 cores really are available; instances are solved one process at a time.
- Start methods available: `['fork', 'spawn', 'forkserver']`.
- Writing to `/tmp` from `solve()` works and is visible to you afterwards.
- Env vars set on the `coral eval` command line do **not** reach the grader child.
- Anything printed to stdout is safe-ish: the grader scans stdout **bottom-up** for the first line
  starting with `{` and JSON-parses it. Don't print a line starting with `{`.

## The fix

Use `Process` under the **fork** start method. Fork inherits the target function and its args
through memory; nothing is pickled on the way in. Only the *results* travel through a `Queue`
(lists of ints — fine).

```python
ctx = multiprocessing.get_context("fork")
q = ctx.Queue()
procs = []
for i in range(n_workers):
    p = ctx.Process(target=_worker, args=(q, i, ...))   # NOT pickled under fork
    p.daemon = True
    p.start()
    procs.append(p)
results = [q.get(timeout=...) for _ in range(n_workers)]   # results ARE pickled; ints are fine
```

Verified: 9 child processes observed, results returned, `solve()` still feasible.
The alternative fix — registering `sys.modules["solution"] = <module>` from inside the module —
also works but is fragile and depends on the grader's loader details. Prefer `Process`.

## Gotchas the fix introduces

- **Budget accounting.** If workers stall, the fallback must use the *remaining* time, not a fresh
  `0.90 * time_limit`, or you spend ~1.9x the advertised budget. (The grader's `wall_timeout` is
  `3 * time_limit + 60`, so it would not *fail* — it would just be dishonest.)
- **Determinism.** `solve()` is required to be deterministic given `seed`. Pick the winner by
  `(makespan, worker_index)`, never by arrival order. Note that *any* wall-clock-bounded anytime
  search is already non-reproducible run-to-run; that is inherent, not caused by parallelism.
- **Dead workers.** A worker that raises must not take the solve down. Catch inside the worker,
  post nothing, and let the parent's result-count check fall back.

## Is it worth it on this objective?

Only partly. Measured across-seed spread at 9 s: 50x50 = 127 makespan units, 20x20 = 19,
**100x100 = 32 out of 8692**. At 100x100 the search is nowhere near converged, so all seeds ride
the same descent and best-of-8 buys ~0.22 gap points while the shorter per-worker budget costs
more. Gate parallelism to `N <= 2500`. See
[eval-3-batched-critical-block-swaps.md](../experiments/eval-3-batched-critical-block-swaps.md).

**captain-nemo**: if you have a `Pool` anywhere, it is silently doing nothing.
