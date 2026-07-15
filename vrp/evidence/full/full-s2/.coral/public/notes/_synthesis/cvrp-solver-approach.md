---
creator: captain-nemo
created: 2026-07-14T03:00:00
type: synthesis
claim: "Clarke-Wright + Sweep dual construction + RVND + ILS with adaptive perturbation achieves 0.989 on 50 hidden CVRP instances"
status: confirmed
confidence: high
supersedes: []
tags: [cvrp, synthesis]
---

# CVRP Solver: CW + Sweep + RVND + ILS achieves 0.989

**Summary:** A pure-Python CVRP solver using Clarke-Wright and Sweep dual construction, 5 RVND neighborhoods (2-opt, Or-opt, Relocate, Exchange, 2-opt*), and ILS with adaptive perturbation (CROSS-exchange + double-bridge) achieves 0.989 on 50 hidden 100-customer instances.

**Best score: 0.9889** (eval 5, commit baeaf95d)

**Evidence:**
- attempt `165199afc49b`: 0.9815 — initial CW + RVND + ILS
- attempt `aa0e2e28fb42`: 0.9875 — prefix sums for 2-opt*, double-bridge perturbation
- attempt `b75d2c9b735a`: 0.9880 — Sweep + CW dual construction
- attempt `baeaf95da992`: 0.9889 — adaptive perturbation, aggressive restarts
- attempt `dde33ba223e0`: 0.9862 — cross-exchange neighborhood (regression)

**Why it works:**
1. **Dual construction** (CW + Sweep) provides diverse starting points, picking the best for the ILS loop
2. **Prefix sums** make 2-opt* load checks O(1) instead of O(n), enabling more ILS iterations
3. **Adaptive perturbation** (1-3 CROSS-exchange/double-bridge moves) escapes local optima without being destructive
4. **Aggressive fresh restarts** (alternating CW/Sweep with perturbations) ensure diverse exploration

**Confidence:** High for the 0.988-0.989 range. Uncertain whether 0.995+ is achievable with this approach.

**Counter-evidence:** The cross-exchange neighborhood (eval 6) regressed the score, suggesting the current approach is near its local optimum. A fundamentally different technique (population-based search, set partitioning, or exact methods) might be needed to break through.

## Current trajectory

| Eval | Score | Change |
|------|-------|--------|
| 1 | 0.9815 | — |
| 2 | 0.9875 | +0.006 |
| 3 | 0.9871 | -0.0004 |
| 4 | 0.9880 | +0.0009 |
| 5 | 0.9889 | +0.0009 |
| 6 | 0.9862 | -0.0027 |

## Open problems

1. **Hard tail**: G100_3256_01 (5.94% gap), G100_3173_01 (4.7%), G100_3215_01 (3.6%) are the hardest instances. The cross-exchange helped G100_3256_01 (5.9% → 0.7%) but was too slow overall.
2. **Time budget**: The solver uses the full 10s per instance. Any additional computation (new neighborhoods, more perturbations) reduces ILS iterations and hurts the score.
3. **Deterministic construction**: CW and Sweep are deterministic. The solver relies on random perturbations for diversity, which may not be sufficient.

## Key decisions

- **Hill-climbing acceptance** beats SA. The problem structure (integer distances, tight local optima) doesn't benefit from random exploration.
- **CROSS-exchange + double-bridge** are the best perturbations. Random relocate/swap is too destructive.
- **Fresh restarts** (build new solution from scratch) beat returning to the best solution. Cycling through the same local optima wastes iterations.