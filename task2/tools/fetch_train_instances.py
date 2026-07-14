"""Download classic JSSP benchmarks into task2/seed/benchmarks/.

These are the OR-Library / Taillard instances with *published* optima, mirrored by
JSPLIB (github.com/tamy0612/JSPLIB). They are visible to the agent purely as
literature calibration — small (10x10 to 20x10) and far easier than the task.

Neither the training set nor the hidden set comes from here:
  * training instances  -> tools/make_train_instances.py  (generated, visible)
  * hidden test set     -> tools/make_hidden_instances.py (generated, private)

    uv run python tools/fetch_train_instances.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/tamy0612/JSPLIB/master"
TRAIN = ["ft10", "ft20", "abz5", "la16", "la21", "la26", "la36", "orb01", "swv01", "ta01"]
OUT = Path(__file__).resolve().parent.parent / "seed" / "benchmarks"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {x["name"]: x for x in json.loads(fetch(f"{BASE}/instances.json"))}

    optima: dict[str, dict] = {}
    for name in TRAIN:
        entry = manifest[name]
        if entry.get("optimum") is None:
            raise SystemExit(f"{name}: no proven optimum in JSPLIB manifest")

        raw = fetch(f"{BASE}/instances/{name}").decode()
        # Strip JSPLIB's leading '#' comment block; keep the numeric payload.
        body = [ln for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
        header = (
            f"# Public benchmark instance '{name}' ({entry['jobs']}x{entry['machines']}), "
            f"published optimum = {entry['optimum']}.\n"
            "# Source: OR-Library / Taillard, mirrored by github.com/tamy0612/JSPLIB\n"
            "# Format: '<n_jobs> <n_machines>' then one line per job of (machine duration) pairs.\n"
        )
        (OUT / f"{name}.jss").write_text(header + "\n".join(body) + "\n")

        optima[name] = {
            "optimum": entry["optimum"],
            "proven": True,
            "jobs": entry["jobs"],
            "machines": entry["machines"],
            "source": "JSPLIB",
        }
        print(f"  {name:<7} {entry['jobs']:>2}x{entry['machines']:<2}  optimum={entry['optimum']:>5}")

    (OUT / "optima.json").write_text(json.dumps(optima, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {len(optima)} instances -> {OUT}")


if __name__ == "__main__":
    main()
