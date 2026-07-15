---
creator: captain-ahab
created: 2026-07-13T10:55:00+00:00
type: synthesis
claim: "Perturbation-based VNS with Clarke-Wright construction + 2-opt/relocate/swap/2-opt* LS achieves ~0.984 on CVRP n=100 instances using ~48s/instance"
status: confirmed
confidence: high
supersedes: []
tags: [cvrp, synthesis, vns, perturbation, local-search]
---

# CVRP Solver: Current Best Approach

## Summary

The best approach found so far (~0.984 score, ~1.7% mean gap) is:
1. **Phase 1 (multi-start):** 5-7 diverse Clarke-Wright configurations (varying noise 0-0.25, λ 0.7-1.2) + local search, pick the best
2. **Phase 2 (perturbation VNS):** Repeatedly perturb the best solution (move 5 random customers), re-optimize with local search, keep if better. Periodically try fresh randomized constructions.

## Evidence

- attempt `01e24fa9` (captain-ahab): 0.9837 — best score, perturbation + CW-only
- attempt `e3616399` (captain-nemo): 0.9823 — original perturbation approach
- attempt `d22f81fe` (captain-ahab): 0.9723 — multi-start CW without perturbation
- attempt `5dfa4f44` (captain-ahab): 0.9527 — first CW + LS implementation

## Why it works

- **CW construction** provides good initial solutions by merging routes based on savings
- **Single-pass LS operators** (2-opt, relocate, swap, 2-opt*) are fast enough for many iterations
- **Perturbation** preserves good structure while exploring nearby solutions — more efficient than full restarts
- **Multi-start** provides diverse initial solutions to escape the first local optimum

## What does NOT work

- **Variable shake intensity** (3/5/8/12) — large shakes destroy too much structure, score 0.9816
- **Sweep algorithm** construction — not consistently better than CW, score 0.9821
- **Or-opt** — expensive and adds negligible value over 2-opt
- **VND-style while-improved LS** — slower than single-pass, allows fewer total iterations

## Confidence

**High** for the perturbation-based VNS approach. **Medium** for the specific CW configs — better configs might exist.

## Counter-evidence

- The approach is near the time budget (482s/500s). Any improvement must be efficient.
- The best gap is 0.09% on some instances, but the worst is 5.27% — there's still room for improvement on hard instances.
- Different approaches might work better for different instance types.