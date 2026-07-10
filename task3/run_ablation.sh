#!/usr/bin/env bash
#
# Task 3 — ablation driver.
#
# Runs the 8 outstanding CORAL runs strictly sequentially. Sequential is not a
# convenience: the grader gives each solver a 10 s *wall-clock* budget per
# instance, so a second run competing for CPU would silently lower the score of
# whichever condition happened to be sharing the box. One run at a time, all 16
# cores, same as the banked Task 2 run.
#
# All three conditions load the SAME task.yaml (../task2/task.yaml) and differ
# only by dotlist overrides, so task.description and task.tips — the text the
# agent actually reads — cannot drift between conditions.
#
#   full        vanilla CORAL (control)
#   noknowledge Condition A: agents.knowledge=false
#   noheartbeat Condition B: agents.heartbeat=[]
#
# Conditions are INTERLEAVED, not blocked, so that any drift over the ~16 h
# (thermal, API latency, model-side load) hits all three conditions alike.
#
# Resumable: a run whose auto_stop.json already exists is skipped, so you can
# ^C this script and re-run it.
#
# Usage (from this directory, inside your own tmux/screen — it runs for hours):
#     ./run_ablation.sh              # all remaining runs
#     ./run_ablation.sh full-2       # just one run id
#
set -uo pipefail

cd "$(dirname "$0")" || exit 1

CORAL=(uv run --project ../coral-upstream coral)
TASK_YAML="../task2/task.yaml"
SEED_REPO="$(cd ../task2/seed && pwd)"
TIMEOUT_SEC=${TIMEOUT_SEC:-14400} # 4 h per run; the banked run took 2 h 01 m
POLL_SEC=${POLL_SEC:-60}
MANIFEST="results/manifest.jsonl"

# runid:condition — interleaved
PLAN=(
  "full-1:full"
  "nok-1:noknowledge"
  "nohb-1:noheartbeat"
  "nok-2:noknowledge"
  "nohb-2:noheartbeat"
  "full-2:full"
  "nok-3:noknowledge"
  "nohb-3:noheartbeat"
)

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { printf '\n!! %s\n' "$*" >&2; exit 1; }

# The handoff's gotcha: `pgrep -f "coral.cli start"` matches this script's own
# command line. The manager is always `python -m coral.cli start` (cli/start.py
# _build_coral_command); the bracket keeps the grep from matching itself.
manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

overrides_for() {
  case "$1" in
    full) : ;;
    noknowledge) echo "agents.knowledge=false" ;;
    noheartbeat) echo "agents.heartbeat=[]" ;;
    *) die "unknown condition: $1" ;;
  esac
}

preflight() {
  command -v tmux >/dev/null || die "tmux not found"
  command -v uv >/dev/null || die "uv not found"
  [ -f "$TASK_YAML" ] || die "missing $TASK_YAML"
  [ -d "$SEED_REPO" ] || die "missing seed repo $SEED_REPO"

  # Without this, `coral start` dies with no logs: git describe --dirty must
  # hash ~3,577 CRLF-dirty files and blows setuptools-scm's 40 s timeout.
  [ "$(git -C ../coral-upstream config core.autocrlf)" = "input" ] \
    || die "run: git -C coral-upstream config core.autocrlf input"

  # Condition A needs the fork's ablation flag; vanilla CORAL has no such field.
  grep -q "knowledge: bool = True" ../coral-upstream/coral/config.py \
    || die "coral-upstream lacks agents.knowledge — check out the task3-ablation branch"

  manager_alive && die "a CORAL manager is already running; \`coral stop\` first"
  mkdir -p results
  log "preflight OK — $(nproc) cores, timeout ${TIMEOUT_SEC}s/run"
}

# Assert the condition actually took effect before spending 2 h on the run.
verify_condition() {
  local rundir="$1" cond="$2" cfg="$1/.coral/config.yaml"
  [ -f "$cfg" ] || { log "  !! no config.yaml written"; return 1; }
  local pub="$rundir/.coral/public"
  case "$cond" in
    full)
      grep -q "knowledge: true" "$cfg" || { log "  !! knowledge not true"; return 1; }
      [ -d "$pub/notes" ] && [ -d "$pub/skills" ] || { log "  !! notes/skills missing"; return 1; }
      [ -s "$pub/heartbeat/_global.json" ] || { log "  !! no global heartbeat"; return 1; }
      ;;
    noknowledge)
      grep -q "knowledge: false" "$cfg" || { log "  !! knowledge not false"; return 1; }
      for d in notes skills roles agents; do
        [ -e "$pub/$d" ] && { log "  !! $pub/$d exists"; return 1; }
      done
      grep -q "consolidate" "$pub/heartbeat/_global.json" 2>/dev/null \
        && { log "  !! consolidate still registered"; return 1; }
      ;;
    noheartbeat)
      # `[]` in a shell string is glob-adjacent; this is where we find out.
      grep -qE "heartbeat: \[\]" "$cfg" || { log "  !! heartbeat list not empty in config"; return 1; }
      local g="$pub/heartbeat/_global.json"
      [ -f "$g" ] && grep -q '"name"' "$g" && { log "  !! global heartbeat actions present"; return 1; }
      for f in "$pub"/heartbeat/*.json; do
        [ -f "$f" ] || continue
        grep -q '"name"' "$f" && { log "  !! heartbeat actions in $(basename "$f")"; return 1; }
      done
      ;;
  esac
  return 0
}

run_one() {
  local runid="$1" cond="$2"
  local rundir="$PWD/results/$cond/$runid"
  local stop_file="$rundir/.coral/public/auto_stop.json"

  if [ -f "$stop_file" ]; then
    log "SKIP $runid ($cond) — already finished"
    return 0
  fi
  rm -rf "$rundir"

  log "START $runid ($cond)"
  local t0=$SECONDS
  # shellcheck disable=SC2046
  "${CORAL[@]}" start -c "$TASK_YAML" \
    "workspace.repo_path=$SEED_REPO" \
    "workspace.results_dir=./results/$cond" \
    "workspace.run_dir=./results/$cond/$runid" \
    $(overrides_for "$cond") || { log "  !! coral start failed"; return 1; }

  # `coral start` detaches; wait for the manager to write the run dir.
  local waited=0
  while [ ! -f "$rundir/.coral/config.yaml" ]; do
    sleep 5; waited=$((waited + 5))
    [ $waited -ge 300 ] && { log "  !! run dir never appeared"; return 1; }
  done

  if ! verify_condition "$rundir" "$cond"; then
    log "  !! condition $cond did not take effect — stopping run, NOT counting it"
    "${CORAL[@]}" stop >/dev/null 2>&1
    return 1
  fi
  log "  condition verified; polling (elapsed check every ${POLL_SEC}s)"

  local status="unknown"
  while :; do
    if [ -f "$stop_file" ]; then status="auto_stop"; break; fi
    if ! manager_alive; then
      sleep 20
      if [ -f "$stop_file" ]; then status="auto_stop"; else status="manager_died"; fi
      break
    fi
    if [ $((SECONDS - t0)) -ge "$TIMEOUT_SEC" ]; then
      log "  !! timeout after ${TIMEOUT_SEC}s — stopping"
      "${CORAL[@]}" stop >/dev/null 2>&1
      status="timeout"
      break
    fi
    sleep "$POLL_SEC"
  done

  local elapsed=$((SECONDS - t0))
  local n_attempts
  n_attempts=$(find "$rundir/.coral/public/attempts" -name '*.json' 2>/dev/null | wc -l)
  log "END   $runid ($cond) status=$status elapsed=$((elapsed / 60))m attempts=$n_attempts"

  printf '{"runid":"%s","condition":"%s","status":"%s","elapsed_sec":%d,"attempts":%d,"run_dir":"%s","finished_at":"%s"}\n' \
    "$runid" "$cond" "$status" "$elapsed" "$n_attempts" "results/$cond/$runid" "$(date -Iseconds)" >> "$MANIFEST"

  [ "$status" = "auto_stop" ]
}

preflight
only="${1:-}"
failed=0
for entry in "${PLAN[@]}"; do
  runid="${entry%%:*}"; cond="${entry##*:}"
  [ -n "$only" ] && [ "$only" != "$runid" ] && continue
  run_one "$runid" "$cond" || { failed=$((failed + 1)); log "  run $runid did not complete cleanly"; }
  # Let the box settle (grader daemon teardown, page cache) before the next run.
  sleep 60
done

log "ALL DONE — $failed run(s) did not reach auto_stop"
log "next: uv run --project ../coral-upstream python analyze.py"
exit $((failed > 0))
