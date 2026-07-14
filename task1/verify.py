"""Independent feasibility check of result/best_program.py.

The grader accepts constraint violations up to 1e-6. Since our sum of radii
exceeds the benchmark by only ~6e-6, we re-verify at machine precision to show
the result does not depend on that slack.

    uv run --with numpy --with scipy python verify.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

BENCHMARK = 2.635977  # AlphaEvolve, as hardcoded in the grader
N = 26


def load_run(path: Path):
    spec = importlib.util.spec_from_file_location("best_program", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def main() -> int:
    centers, radii, reported = load_run(Path(__file__).parent / "result" / "best_program.py")()
    centers = np.asarray(centers, dtype=float)
    radii = np.asarray(radii, dtype=float)

    assert centers.shape == (N, 2), centers.shape
    assert radii.shape == (N,), radii.shape
    assert not np.isnan(centers).any() and not np.isnan(radii).any()
    assert (radii >= 0).all()

    total = float(radii.sum())

    wall_slack = np.minimum.reduce([centers[:, 0], centers[:, 1], 1 - centers[:, 0], 1 - centers[:, 1]])
    wall_violation = float((radii - wall_slack).max())

    dist = np.linalg.norm(centers[:, None] - centers[None, :], axis=-1)
    i, j = np.triu_indices(N, k=1)
    pair_violation = float((radii[i] + radii[j] - dist[i, j]).max())

    worst = max(wall_violation, pair_violation)

    print(f"reported sum   : {reported!r}")
    print(f"recomputed sum : {total:.12f}")
    print(f"score          : {total / BENCHMARK:.9f}")
    print(f"margin vs bench: {total - BENCHMARK:+.3e}")
    print()
    print(f"max wall violation : {wall_violation:.3e}")
    print(f"max pair violation : {pair_violation:.3e}")
    print(f"grader tolerance   : {1e-6:.3e}")
    print()
    print(f"distinct centers   : {len(np.unique(np.round(centers, 9), axis=0))}/{N}")
    print(f"min / max radius   : {radii.min():.6f} / {radii.max():.6f}")
    print()

    # The margin must dominate the violation, else the score is tolerance slack.
    ok = worst <= 1e-9 and total > BENCHMARK
    print(f"feasible at 1e-9   : {worst <= 1e-9}")
    print(f"beats benchmark    : {total > BENCHMARK}")
    print(f"margin / violation : {(total - BENCHMARK) / max(worst, 1e-300):.3e}x")
    print()
    print("VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
