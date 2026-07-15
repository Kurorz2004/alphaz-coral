# Connections Map

## CW + Sweep dual construction
- Links: eval-4-sweep-dual-construction.md, eval-5-adaptive-perturbation.md
- Pattern: Using two fundamentally different construction heuristics and picking the best gives a stronger starting point for ILS.
- Implication: Other agents should try dual construction with their own heuristics.

## Prefix sums for neighborhood efficiency
- Links: eval-2-prefix-sums-double-bridge.md, eval-5-adaptive-perturbation.md
- Pattern: Making the neighborhood load checks O(1) via prefix sums significantly speeds up the local search.
- Implication: Any O(n) computation inside an O(n²) loop is a bottleneck. Profile and optimize.

## Adaptive perturbation
- Links: eval-5-adaptive-perturbation.md, eval-6-cross-exchange.md
- Pattern: When stuck, apply stronger perturbations. But the perturbation type matters — CROSS-exchange + double-bridge works, random relocate/swap doesn't.
- Implication: Perturbation quality matters more than quantity. Controlled perturbations beat random ones.

## Team Roster (2026-07-14)

### Role coverage
- **captain-nemo** (gen 1): Engineer with performance-engineering tilt. CW + Sweep + RVND + ILS lane. 0.9889.
- **captain-ahab** (gen 0): Seeded role — no evidence-backed description yet. Score 0.986.

### Lane coverage
- **captain-nemo**: CW + Sweep dual construction, RVND (5 neighborhoods), ILS with adaptive perturbation.
- **captain-ahab**: Clarke-Wright + ILS with delta-based neighborhoods. Similar approach but slightly lower score.

### Posture coverage
- Both agents are **engineers** — building and iterating on the solver. 
- **Missing postures**: No researcher (literature review), no performance engineer (profiling), no reviewer (falsifying claims), no tech writer (synthesis).
- **Risk**: Both agents are converging on the same approach. If the current approach plateaus, there's no agent exploring fundamentally different techniques.

### Stale focus notes
- No focus notes found. Both agents are iterating without explicit focus declarations.