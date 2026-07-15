# Open Questions

## Can Guided Local Search improve the perturbation-based approach?
**Status:** no experiments yet
**Why it matters:** GLS systematically penalizes frequently-used edges, which could help escape local optima that perturbation alone can't handle. The current approach relies on random perturbation, which is inefficient.
**Cheapest first experiment:** Add edge penalties to the LS objective, penalize the edges in the best solution after each perturbation cycle, and restart.

## Can Record-to-Record Travel (RRT) improve the search?
**Status:** no experiments yet
**Why it matters:** RRT allows uphill moves within a threshold, which could help escape local optima without the randomness of perturbation. It's simpler than SA and may be more effective.
**Cheapest first experiment:** During LS, accept moves that increase distance by up to 1% of the current best distance.

## What makes the hard instances hard?
**Status:** no experiments yet
**Why it matters:** Some instances have 5%+ gaps while others are near-optimal. Understanding the difference would help target improvements.
**Cheapest first experiment:** Analyze the instance characteristics (capacity, distance distribution, number of routes in best solution) for the hardest vs easiest instances.

## Is there a better construction than Clarke-Wright?
**Status:** partially explored (sweep tried, didn't work)
**Why it matters:** The construction determines the initial solution, which constrains the LS. A better construction could reduce the gap without needing more LS iterations.
**Cheapest first experiment:** Try a cheapest-insertion heuristic, or a greedy randomized construction with a restricted candidate list (GRASP-style).

## Can we make the local search faster?
**Status:** no experiments yet
**Why it matters:** The time budget is the binding constraint. If each LS pass were 2x faster, we could run 2x more perturbation cycles.
**Cheapest first experiment:** Implement incremental delta computation in relocate/swap (compute only affected edges instead of full route distance).