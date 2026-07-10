# Task 3 — Ablation Study

Which CORAL mechanism actually matters for the job-shop scheduling task of Task 2?

| Condition | Change | Runs |
|---|---|---|
| **Full CORAL** (control) | none | 3 |
| **A — no knowledge** | `agents.knowledge=false` | 3 |
| **B — no heartbeats** | `agents.heartbeat=[]` | 3 |

All nine runs use **`agents.model=sonnet`**, not the Opus of Task 2 — see
*The model is sonnet* below. Absolute scores are therefore not comparable to Task 2's
headline number; every arm shares the model, so the ablation comparison is unaffected.

Every run uses the **same** `../task2/task.yaml` — same objective text, same tips,
same seed, same hidden instances, same `max_real_attempts: 12`, no `score_threshold`.
Conditions are expressed purely as dotlist overrides, so the prompt the agent reads
cannot drift between arms.

## What each condition required

**Condition B: `agents.heartbeat: []` is a silent no-op in stock CORAL.** Two
independent mechanisms regrow the list, and both must be defeated:

1. `_preprocess` (`coral/config.py`) back-fills every default action the user did not
   *name*. An empty list names nothing, so `heartbeat: []` in task.yaml regrows **all
   four** defaults — byte-identical to not setting it at all.
2. `write_agent_heartbeat` / `write_global_heartbeat` re-add `PROTECTED_LOCAL={reflect}`
   / `PROTECTED_GLOBAL={consolidate}` whenever missing. This bites even the dotlist form
   (`agents.heartbeat=[]`), which bypasses `_preprocess`.

Both were confirmed by running pristine `upstream-base` in a git worktree and counting
heartbeat firings over 12 simulated evals: the default config and `heartbeat: []`
produced the *same* 18 firings.

**B did not strictly require a code change.** Naming all four actions with an
unreachable interval defeats both regrowth paths, because interval actions fire on
`count % every == 0`, plateau actions on `streak >= every`, and `every` has no upper
bound:

```yaml
agents:
  heartbeat:
    - {name: reflect,     every: 1000000}
    - {name: consolidate, every: 1000000, global: true}
    - {name: pivot,       every: 1000000, trigger: plateau}
    - {name: lint_wiki,   every: 1000000, global: true}
```

(Not `every: 0` — `count % 0` raises `ZeroDivisionError`.) This is pinned by
`test_unreachable_every_disables_heartbeats_without_any_code_change`. We ran B via the
fixed `heartbeat: []` instead, because the trick leaves four phantom actions visible to
the agent in `coral heartbeat` output while CORAL.md is inviting it to
`coral heartbeat set reflect --every 3`. **So the `protect` / `_preprocess` fixes are a
defect fix, not a prerequisite for the arm.**

**Condition A genuinely has no built-in switch.** `SharingConfig`
(`sharing.notes` / `.skills` / `.attempts`, `config.py:315`) looks like exactly the
right knob and is **dead config** — nothing in the upstream package ever reads
`config.sharing`. So A is a new field, `agents.knowledge`. When false:

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
rendered `CORAL.md` matches byte-for-byte. So the control arm runs vanilla CORAL, even
though it runs it through the fork.

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

## The model is sonnet

The first attempt at this experiment ran on Opus and died on the API quota. Two Opus
agents exhausted the rolling **5-hour** window in **2 h 50 m**. After that the agents
exited 1 on every turn, the manager restarted them, the crash-burst breaker paused
them, and one agent churned through 33 sessions producing nothing. The control run
reached 10 real evals, never hit its 12th, never auto-stopped, and died on the driver's
timeout — 78 `five_hour` rejections in its logs.

The quota window is shared across models and Opus drains it several times faster, so
the whole ablation runs on sonnet. `analyze.py` refuses to pool runs whose recorded
`agents.model` differs from its `TARGET_MODEL`, and flags any run with a rate-limit
rejection in its agent logs. The driver detects a rejection, kills the run, sleeps
until the `resetsAt` epoch the agent logged, and retries from scratch.

## Two leaks the audit caught, that inspection did not

Condition A looked clean in the config and in `CORAL.md`, and was still leaking:

1. **The worktree symlinks.** `setup_shared_state` linked every shared-state item
   unconditionally. With the knowledge dirs deleted the links *dangled*, so
   `ls .claude/` still showed the agent a `notes/` and a `skills/` directory.
2. **The restart prompt.** `_build_score_prompt`, injected on every agent respawn and
   entirely separate from `CORAL.md`, told Condition A agents to *"Check what other
   agents have tried via `coral log -n 10`, `coral notes`, and `coral skills`"* and to
   *"Consolidate scattered notes, distill reusable skills."*

Both are fixed and pinned by regression tests. The lesson generalises: an ablation is
only as good as the audit that checks it from the run's artifacts, because a flag
proves intent, not effect.

**One confound we cannot remove.** The agent subprocess is Claude Code, which carries
its *own* global skills — including one named `deep-research`. CORAL's seeded copy is
ablated; the user-level one is not, and is present in every arm. So Condition A removes
CORAL's research scaffold, not the agent's. Since it is identical across arms it cannot
bias the comparison, but the claim is "no CORAL knowledge channel", not "no skills".

## Running it

Sequential, one run at a time. This is not a convenience: the grader gives each
solver a 10 s **wall-clock** budget per instance, so a concurrent run would silently
cost whichever condition shared the box. 9 runs × ~2 h ≈ 18 h.

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
    ├── full/          full-s1..s3
    ├── noknowledge/   nok-s1..s3
    └── noheartbeat/   nohb-s1..s3
```

Task 4 should branch from `task3-ablation`: its "vanilla CORAL" arm is this branch
with `agents.knowledge` left at its default, which the byte-identity test pins to
upstream behaviour.
