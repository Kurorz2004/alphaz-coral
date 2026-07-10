# Task 3 — Ablation Study

Which CORAL mechanism actually matters for the job-shop scheduling task of Task 2?

| Condition | Change | Runs |
|---|---|---|
| **Full CORAL** (control) | none | 3 (1 banked from Task 2 + 2 new) |
| **A — no knowledge** | `agents.knowledge=false` | 3 |
| **B — no heartbeats** | `agents.heartbeat=[]` | 3 |

Every run uses the **same** `../task2/task.yaml` — same objective text, same tips,
same seed, same hidden instances, same `max_real_attempts: 12`, no `score_threshold`.
Conditions are expressed purely as dotlist overrides, so the prompt the agent reads
cannot drift between arms.

## Both conditions needed a code change

Neither ablation was expressible in vanilla CORAL. The fork
(`coral-upstream`, branch `task3-ablation`) adds them.

**Condition B was not free.** `agents.heartbeat: []` looks like it disables
heartbeats, but `write_agent_heartbeat` / `write_global_heartbeat` re-add the
`PROTECTED_LOCAL` / `PROTECTED_GLOBAL` actions whenever they are missing. An empty
list still produced `reflect` every eval and `consolidate` every 10 global evals —
condition B would have been a near no-op and nobody would have noticed. Both writers
now take `protect`, and the manager passes `protect=False` when the list is empty by
design. Regression test: `tests/test_knowledge_ablation.py::test_empty_heartbeat_list_is_honoured_only_without_protect`.

**Condition A is a new config field**, `agents.knowledge`. When false:

- `notes/`, `skills/`, `agents/`, `roles/` are neither created nor seeded;
- no bundled skills (`deep-research`, `create-notes`, `organize-files`, `skill-creator`)
  and no bundled subagents (`deep-researcher`, `librarian`);
- the note-curating heartbeats (`consolidate`, `lint_wiki`) are dropped, and
  `reflect` / `pivot` fall back to note-free prompts that keep the reflection and the
  direction-change but ask for no artifact;
- the 21 knowledge-dependent regions of `CORAL.md` are swapped for knowledge-free text.

Attempts, the leaderboard, eval messages and `coral show --diff` are untouched.
Agents still read each other's code and scores — **A removes the curated channel, not
all cross-agent transfer.** That is the honest scope of the claim.

### Why the control is trustworthy

`agents.knowledge` defaults to `true` and is a no-op in that state *by construction*,
not by inspection: the ON text of every template region was extracted verbatim from
the pre-flag template, and `test_knowledge_on_renders_byte_identical_to_upstream`
renders upstream's template straight out of git (`upstream-base` tag) and asserts the
rendered `CORAL.md` matches byte-for-byte. That is what lets the banked Task 2 run be
pooled with the two new full-CORAL runs.

### Known overlaps and confounds, stated up front

1. **A and B overlap on two heartbeat actions.** `consolidate` and `lint_wiki` exist
   only to write and curate notes; they are part of the knowledge system, so A drops
   them. B drops all four. The conditions are therefore not orthogonal, and neither
   the spec nor CORAL's design makes them so.
2. **B also removes the per-eval score header.** In `manager.py` the `if not actions:
   continue` guard sits *above* the code that builds the `## Eval #N Results` block,
   so with no heartbeat actions the agent never gets that injected summary. It still
   sees its score — `coral eval` blocks and prints it — but it loses the framing.
   This is vanilla behaviour, not something the fork introduced; `analyze.py` counts
   the missing headers rather than papering over them.
3. **A removes the `deep-research` skill** because it is a bundled skill. The
   *capability* is preserved: the knowledge-free `CORAL.md` still tells agents to use
   web search for literature review. What is ablated is the scaffold, not the tool.

## Running it

Sequential, one run at a time. This is not a convenience: the grader gives each
solver a 10 s **wall-clock** budget per instance, so a concurrent run would silently
cost whichever condition shared the box. 8 runs × ~2 h ≈ 16 h.

`coral start` spawns headless `claude` subprocesses, so **you** must launch it:

```bash
# from a tmux/screen session you can detach from — this runs for hours
cd task3 && ./run_ablation.sh
```

The driver is resumable (a run with an `auto_stop.json` is skipped), interleaves the
conditions so drift over 16 h hits all arms alike, and **verifies each condition took
effect before spending two hours on it** — it reads back `.coral/config.yaml`, the
seeded directories, and the heartbeat JSON, and aborts the run if the override did
not land.

```bash
uv run --project ../coral-upstream python analyze.py
```

`analyze.py` re-derives every condition from the run's own artifacts rather than
trusting the config: it counts `## Heartbeat:` prompts and `## Eval #` headers in the
agent logs, checks that no ablated directory exists, and greps for references to
assets that should not have been reachable. A run that fails an integrity check is
reported and **excluded from the statistics** instead of silently averaged in.

With n=3 per arm the smallest attainable two-sided exact Mann-Whitney p is 0.10, and
only under complete separation. The report leads with the raw scores and the effect
size; p is a tiebreak, not a verdict.

## Layout

```
task3/
├── run_ablation.sh    driver: 8 sequential runs, interleaved, resumable, self-verifying
├── analyze.py         Final Score per run, mean ± std, integrity audit, summary.json
├── REPORT.md          results and what they mean
└── results/           gitignored
    ├── manifest.jsonl one line per completed run
    ├── summary.json   written by analyze.py
    ├── full/          full-1, full-2
    ├── noknowledge/   nok-1, nok-2, nok-3
    └── noheartbeat/   nohb-1, nohb-2, nohb-3
```

Task 4 should branch from `task3-ablation`: its "vanilla CORAL" arm is this branch
with `agents.knowledge` left at its default, which the byte-identity test pins to
upstream behaviour.
