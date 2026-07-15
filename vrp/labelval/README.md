# Label validation — is the HGS reference trustworthy?

The 50 hidden instances have **no known optimum** (that is the point — a published optimum
is a lookup cheat). Their reference distances are computed by us with PyVRP HGS. This
directory is the evidence that those references are good enough to score against.

**Method.** Run HGS on *frozen XML100 instances whose optima ARE proven* — same generator,
same distribution as ours — and measure how far it lands from ground truth. 420 runs:
30 instances × {2, 5, 10, 30}s × 3 seeds (free fleet), plus 60 pinned-fleet runs.

## Findings

| HGS budget | % exactly optimal | mean gap | worst gap |
|---|---|---|---|
| 2 s | 6.7% | 0.82% | 1.94% |
| 10 s | 26.7% | 0.28% | 1.15% |
| 30 s | 56.7% | 0.11% | 0.62% |
| best-of-3 × 30 s | 66.7% | **0.068%** | 0.62% |

HGS does **not** reliably reach the optimum — it misses on ~1/3 of instances even at 30 s.
But it misses *small*, and it never once beat a proven optimum (0/420), which also confirms
the published optima are free-fleet, i.e. our formulation matches theirs.

Crucially the reference is a **fixed per-instance constant shared by every ablation
condition**, so `score_A / score_B` is exactly invariant to its error. Label error shifts
the absolute score by ~0.1%; it cannot bias the between-condition comparison.

**Rounding.** `round_func='round'` is exactly the grader's `int(sqrt(dx²+dy²) + 0.5)` —
verified elementwise on all 255,025 node pairs, and by re-scoring HGS's own routes under the
grader's formula on all 360 free-fleet runs (0 mismatches). It cannot fail: `sqrt` of an
integer is never exactly `k+0.5`, so half-even and half-up never disagree on integer coords.

**Fleet.** `k = ceil(total_demand/capacity)` is **wrong** — the proven optimum needs more
routes than that 11.8% of the time (57.4% at small route sizes), by up to +10. Pinning `k`
there can make the instance infeasible. Hence the non-binding fleet.

**Data defect found.** 91 of the 10,000 published XML100 `.sol` files (0.91%) are malformed:
a customer is visited twice (e.g. `XML100_1121_04` has customer 33 in both Route #5 and #23).
Listed in `corrupt_sols.txt`; excluded from the sample.

## Known limitations (stated, not buried)

- The 30-instance sample was drawn with `A = i%3+1, D = i%6+1`, which **aliases A to D**. All
  factor levels appear, so the *pooled* gap numbers above are sound, but any **per-factor**
  breakdown is confounded. `sample30b.py` de-aliases it and was never run.
- **30 s is not saturated** — 10 s → 30 s was still improving (0.28% → 0.11%). 60 s+ was never
  tested, so "30 s is the right budget" is a cost/benefit call, not a measured optimum.

## Files

| File | |
|---|---|
| `results.csv` | the 420 runs — the raw evidence |
| `common.py` | grader-identical distance fn + HGS wrapper |
| `verify_round.py` | proves `round_func='round'` matches the grader |
| `audit_all_sols.py` → `corrupt_sols.txt` | the 91 malformed published solutions |
| `fleet_analysis.py` | the `ceil(demand/cap)` disproof |
| `run_hgs.py`, `analyze.py` | the experiment and its aggregation |

## Re-running

These scripts read the frozen XML100 corpus, which is **not committed** (100 MB). Re-download:

```bash
mkdir -p data/xml100 && cd data/xml100
B=https://galgos.inf.puc-rio.br/cvrplib/uploads/files/xml100
curl -O $B/instances.7z && curl -O $B/solutions.7z
python -c "import py7zr;[py7zr.SevenZipFile(f).extractall('.') for f in ('instances.7z','solutions.7z')]"
```

`results.csv` is committed, so the findings above are checkable without the download.
