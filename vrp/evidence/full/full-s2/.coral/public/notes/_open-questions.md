# Open Questions

## G100_3256_01: What makes this instance so hard?

**Claim A:** The cross-exchange neighborhood helped this instance from 5.94% to 0.7% gap (eval 6), suggesting segment-exchange is the key to solving it.

**Claim B:** The current solver (CW + Sweep + RVND + ILS) can't get below 5.94% on this instance without the cross-exchange.

**Status:** Unresolved. The cross-exchange helped but was too slow for other instances. A faster cross-exchange (limited search) might help.

**Cheapest first experiment:** Add cross-exchange as a perturbation (not a local search move) and test on dev.

## What is the maximum score achievable with pure-Python heuristics?

**Status:** No experiments yet. The best score is 0.9889. Reference solutions (HGS, UHGS) achieve 1.0+, but they use C++ and population-based methods.

**Why it matters:** If 0.99 is the ceiling for pure heuristics, the team should explore different approaches. If 0.995+ is possible, we should optimize further.

**Cheapest first experiment:** Run the current best solver with 2x time budget (20s) to see if more iterations help. If not, the approach is near its ceiling.

## Can a different construction heuristic beat CW + Sweep?

**Status:** No experiments yet. The team uses CW and Sweep. Other heuristics (random insertion, nearest-neighbor, giant tour splitting) might give better initial solutions.

**Why it matters:** A better initial solution means fewer ILS iterations needed to find a good solution, leaving more time for exploration.

**Cheapest first experiment:** Implement a random insertion heuristic and compare to CW + Sweep on dev.

## Is the perturbation strength optimal?

**Status:** Partial. We know that 1-3 perturbations (adaptive) is better than 1 (fixed) or 5+ (too destructive). But the optimal schedule is unknown.

**Why it matters:** The perturbation is the main exploration mechanism. Suboptimal perturbation means wasted iterations.

**Cheapest first experiment:** Sweep different perturbation strength schedules (1-2, 1-4, 2-3) on tune mode.