#!/usr/bin/env bash
#
# Task 4 — comparative experiment driver: the publication-gate arm.
#
# Runs 3 gate-on runs strictly sequentially (same reason as run_ablation.sh:
# the grader gives each solver a 10 s wall-clock budget per instance, so a
# second run competing for CPU would silently lower scores). The vanilla arm
# of the comparison is the Task 3 `full` runs (results/full/full-s{1,2,3}):
# flag off is byte-identical to the code those runs used, so they are reused
# rather than re-paid.
#
# Same task.yaml as every other arm; the only delta is the dotlist override
#   agents.publication_gate=true
# on top of the identical model/agents/budget configuration.
#
# Resumable: a run whose auto_stop.json already exists is skipped.
#
# Usage (from this directory, inside tmux/screen — runs for hours):
#     ./run_gate.sh              # all remaining gate runs
#     ./run_gate.sh gate-s2      # just one run id
#
set -uo pipefail

cd "$(dirname "$0")" || exit 1

CORAL=(uv run --project ../coral-upstream coral)
TASK_YAML="./task.yaml"
SEED_REPO="$(cd ./seed && pwd)"
MODEL=${MODEL:-deepseek-v4-flash} # must match the vanilla arm (full-s*)
TIMEOUT_SEC=${TIMEOUT_SEC:-14400} # 4 h per run
POLL_SEC=${POLL_SEC:-60}
MAX_TRIES=${MAX_TRIES:-2}
MANIFEST="results/manifest.jsonl"
SHARED_DIR=".claude" # claude_code runtime, same as every prior arm

PLAN=(
  "gate-s1:gate"
  "gate-s2:gate"
  "gate-s3:gate"
)

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { printf '\n!! %s\n' "$*" >&2; exit 1; }

manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

overrides_for() {
  case "$1" in
    gate) echo "agents.publication_gate=true" ;;
    *) die "unknown condition: $1" ;;
  esac
}

# --- API quota handling (verbatim from run_ablation.sh) -----------------------

rate_limited() {
  grep -rlq --include='*.log' '"status":"rejected"' "$1/.coral/public/logs" 2>/dev/null
}

reset_epoch() {
  grep -rho --include='*.log' '"resetsAt":[0-9]*' "$1/.coral/public/logs" 2>/dev/null |
    grep -o '[0-9]*' | sort -n | tail -1
}

wait_for_reset() {
  local rundir="$1" now epoch
  epoch=$(reset_epoch "$rundir")
  now=$(date +%s)
  if [ -z "$epoch" ] || [ "$epoch" -le "$now" ]; then
    log "  no future reset timestamp — waiting 30 min as a fallback"
    sleep 1800
    return
  fi
  local secs=$((epoch - now + 120))
  log "  quota resets at $(date -d "@$epoch" +%H:%M:%S) — sleeping ${secs}s ($((secs / 60))m)"
  sleep "$secs"
}

wait_for_seed() {
  local rundir="$1" want=$((2 + 1)) waited=0 # agents.count=2, plus _global.json
  while :; do
    local n
    n=$(find "$rundir/.coral/public/heartbeat" -name '*.json' 2>/dev/null | wc -l)
    [ "$n" -ge "$want" ] && return 0
    sleep 5
    waited=$((waited + 5))
    if [ $waited -ge 900 ]; then
      log "  !! only $n/$want heartbeat files after ${waited}s"
      return 1
    fi
  done
}

# Assert the gate actually took effect before spending hours on the run.
# Config alone is not proof; the observable difference is that each agent
# worktree's notes/ and skills/ are REAL DIRECTORIES, not symlinks, while
# attempts/ stays a symlink.
verify_condition() {
  local rundir="$1" cfg="$1/.coral/config.yaml"
  [ -f "$cfg" ] || { log "  !! no config.yaml written"; return 1; }
  local pub="$rundir/.coral/public"
  grep -q "model: $MODEL" "$cfg" || { log "  !! model is not $MODEL"; return 1; }
  grep -q "publication_gate: true" "$cfg" || { log "  !! publication_gate not true in config"; return 1; }
  grep -q "knowledge: true" "$cfg" || { log "  !! knowledge not true"; return 1; }
  [ -d "$pub/notes" ] && [ -d "$pub/skills" ] || { log "  !! shared notes/skills missing"; return 1; }
  grep -q "consolidate" "$pub/heartbeat/_global.json" || { log "  !! no global heartbeat"; return 1; }

  local n_worktrees=0
  for wt in "$rundir"/agents/*/; do
    [ -d "$wt" ] || continue
    n_worktrees=$((n_worktrees + 1))
    local nd="$wt$SHARED_DIR/notes" sd="$wt$SHARED_DIR/skills" ad="$wt$SHARED_DIR/attempts"
    [ -d "$nd" ] || { log "  !! $nd missing"; return 1; }
    [ -L "$nd" ] && { log "  !! $nd is a symlink — gate NOT applied"; return 1; }
    [ -d "$sd" ] || { log "  !! $sd missing"; return 1; }
    [ -L "$sd" ] && { log "  !! $sd is a symlink — gate NOT applied"; return 1; }
    [ -L "$ad" ] || { log "  !! $ad is not a symlink — worktree layout unexpected"; return 1; }
  done
  [ "$n_worktrees" -ge 2 ] || { log "  !! only $n_worktrees agent worktrees found"; return 1; }
  log "  gate verified: $n_worktrees worktrees with real notes/skills dirs"
  return 0
}

case "$MODEL" in
  sonnet) EXPECT_MODEL=${EXPECT_MODEL:-deepseek-v4-pro} ;;
  opus)   EXPECT_MODEL=${EXPECT_MODEL:-claude-opus} ;;
  haiku)  EXPECT_MODEL=${EXPECT_MODEL:-claude-haiku} ;;
  *)      EXPECT_MODEL=${EXPECT_MODEL:-$MODEL} ;;
esac

actual_model() {
  grep -rhoE '"model":"[^"]+"' "$1/.coral/public/logs" 2>/dev/null |
    sed -E 's/.*:"(.*)"/\1/' | grep -v '^<synthetic>$' |
    sort | uniq -c | sort -rn | head -1 | awk '{print $2}'
}

verify_actual_model() {
  local rundir="$1" waited=0 m=""
  while [ $waited -lt 600 ]; do
    m=$(actual_model "$rundir")
    [ -n "$m" ] && break
    sleep 10
    waited=$((waited + 10))
  done
  [ -z "$m" ] && { log "  !! no model string in agent logs after ${waited}s"; return 1; }
  case "$m" in
    *"$EXPECT_MODEL"*) log "  actual model = $m"; return 0 ;;
    *) log "  !! actual model is '$m', expected *${EXPECT_MODEL}*"; return 1 ;;
  esac
}

stop_run() {
  "${CORAL[@]}" stop >/dev/null 2>&1
  local drain=0
  while manager_alive && [ $drain -lt 180 ]; do sleep 10; drain=$((drain + 10)); done
}

attempt_run() {
  local runid="$1" cond="$2" rundir="$3"
  local stop_file="$rundir/.coral/public/auto_stop.json"
  rm -rf "$rundir"

  local t0=$SECONDS
  # shellcheck disable=SC2046
  "${CORAL[@]}" start -c "$TASK_YAML" \
    "agents.model=$MODEL" \
    "workspace.repo_path=$SEED_REPO" \
    "workspace.results_dir=./results/$cond" \
    "workspace.run_dir=./results/$cond/$runid" \
    $(overrides_for "$cond") >/dev/null 2>&1 || { echo "start_failed"; return; }

  local waited=0
  while [ ! -f "$rundir/.coral/config.yaml" ]; do
    sleep 5; waited=$((waited + 5))
    [ $waited -ge 300 ] && { echo "no_run_dir"; return; }
  done

  if ! wait_for_seed "$rundir" || ! verify_condition "$rundir"; then
    stop_run
    echo "condition_not_applied"
    return
  fi
  if ! verify_actual_model "$rundir"; then
    stop_run
    echo "wrong_model"
    return
  fi
  log "  condition verified (model=$MODEL); polling every ${POLL_SEC}s"

  while :; do
    [ -f "$stop_file" ] && { echo "auto_stop"; return; }
    if rate_limited "$rundir"; then
      log "  !! API quota exhausted — killing run"
      stop_run
      echo "rate_limited"
      return
    fi
    if ! manager_alive; then
      sleep 20
      [ -f "$stop_file" ] && { echo "auto_stop"; return; }
      echo "manager_died"; return
    fi
    if [ $((SECONDS - t0)) -ge "$TIMEOUT_SEC" ]; then
      log "  !! timeout after ${TIMEOUT_SEC}s"
      stop_run
      echo "timeout"; return
    fi
    sleep "$POLL_SEC"
  done
}

run_one() {
  local runid="$1" cond="$2"
  local rundir="$PWD/results/$cond/$runid"

  if [ -f "$rundir/.coral/public/auto_stop.json" ]; then
    log "SKIP $runid ($cond) — already finished"
    return 0
  fi

  local try=1 status=""
  while [ $try -le "$MAX_TRIES" ]; do
    log "START $runid ($cond) try $try/$MAX_TRIES"
    local t0=$SECONDS
    status=$(attempt_run "$runid" "$cond" "$rundir")
    local elapsed=$((SECONDS - t0))
    local n_attempts
    n_attempts=$(find "$rundir/.coral/public/attempts" -name '*.json' 2>/dev/null | wc -l)
    log "END   $runid ($cond) status=$status elapsed=$((elapsed / 60))m attempts=$n_attempts"

    printf '{"runid":"%s","condition":"%s","model":"%s","try":%d,"status":"%s","elapsed_sec":%d,"attempts":%d,"run_dir":"%s","finished_at":"%s"}\n' \
      "$runid" "$cond" "$MODEL" "$try" "$status" "$elapsed" "$n_attempts" \
      "results/$cond/$runid" "$(date -Iseconds)" >>"$MANIFEST"

    [ "$status" = "auto_stop" ] && return 0
    if [ "$status" = "rate_limited" ]; then
      wait_for_reset "$rundir"
      try=$((try + 1))
      continue
    fi
    return 1
  done
  log "  $runid exhausted $MAX_TRIES tries"
  return 1
}

# --- preflight ---------------------------------------------------------------
command -v tmux >/dev/null || die "tmux not found"
command -v uv >/dev/null || die "uv not found"
[ -f "$TASK_YAML" ] || die "missing $TASK_YAML"
[ -d "$SEED_REPO" ] || die "missing seed repo $SEED_REPO"
[ "$(git -C ../coral-upstream config core.autocrlf)" = "input" ] ||
  die "run: git -C coral-upstream config core.autocrlf input"
# The gate arm needs the publication-gate branch checked out.
[ "$(git -C ../coral-upstream branch --show-current)" = "task4-publication-gate" ] ||
  die "coral-upstream must be on task4-publication-gate"
grep -q "publication_gate: bool = False" ../coral-upstream/coral/config.py ||
  die "coral-upstream lacks agents.publication_gate — wrong branch?"
manager_alive && die "a CORAL manager is already running; \`coral stop\` first"

# --- main --------------------------------------------------------------------
mkdir -p results/gate
log "preflight OK — model=$MODEL, $(nproc) cores, timeout ${TIMEOUT_SEC}s/run"

only="${1:-}"
failed=0
for entry in "${PLAN[@]}"; do
  runid="${entry%%:*}"; cond="${entry##*:}"
  [ -n "$only" ] && [ "$only" != "$runid" ] && continue
  run_one "$runid" "$cond" || { failed=$((failed + 1)); log "  run $runid did not complete cleanly"; }
  sleep 60 # let the box settle (grader daemon teardown, page cache)
done

log "GATE ARM DONE — $failed run(s) did not reach auto_stop"
exit $((failed > 0))
