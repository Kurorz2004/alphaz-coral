#!/usr/bin/env bash
#
# run_nohb_s3.sh — standalone run script for nohb-s3 (Condition B, deepseek)
#
# Condition B (noheartbeat): agents.heartbeat=[] — all four heartbeat actions
# (reflect, consolidate, pivot, lint_wiki) are disabled. This also removes the
# per-eval score header block that the manager injects above the heartbeat loop.
#
# Model: deepseek-v4-pro (s3 = deepseek series). The settings.json alias maps
# sonnet→deepseek; we keep it active. MODEL=sonnet in config.yaml but the agent
# actually loads deepseek-v4-pro.
#
# Self-contained — does NOT call run_ablation.sh. Run directly:
#     ./run_nohb_s3.sh
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1

# --- constants ----------------------------------------------------------------
RUNID="nohb-s3"
CONDITION="noheartbeat"
MODEL="sonnet"                        # what goes into config.yaml
EXPECT_MODEL="deepseek-v4-pro"        # what the agent actually loads (alias)
TASK_YAML="../task2/task.yaml"
SEED_REPO="$(cd ../task2/seed && pwd)"
TIMEOUT_SEC=${TIMEOUT_SEC:-14400}     # 4 h per run
POLL_SEC=${POLL_SEC:-60}
MAX_TRIES=${MAX_TRIES:-2}
MANIFEST="results/manifest.jsonl"
RUNDIR="$PWD/results/$CONDITION/$RUNID"
CORAL=(uv run --project ../coral-upstream coral)

# --- helpers ------------------------------------------------------------------
log()   { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die()   { printf '\n!! %s\n' "$*" >&2; exit 1; }
manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

# --- rate-limit handling ------------------------------------------------------
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

# --- condition verification ---------------------------------------------------
wait_for_seed() {
  local rundir="$1" want=$((2 + 1)) waited=0
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

verify_condition() {
  local rundir="$1"
  local cfg="$rundir/.coral/config.yaml"
  [ -f "$cfg" ] || { log "  !! no config.yaml written"; return 1; }
  local pub="$rundir/.coral/public"

  grep -q "model: $MODEL" "$cfg" || { log "  !! model is not $MODEL in config.yaml"; return 1; }

  # Condition B: heartbeat list must be empty
  grep -qE "heartbeat: \[\]" "$cfg" || { log "  !! heartbeat list not empty in config"; return 1; }
  for f in "$pub"/heartbeat/*.json; do
    [ -f "$f" ] || continue
    grep -q '"name"' "$f" && { log "  !! heartbeat actions in $(basename "$f")"; return 1; }
  done

  return 0
}

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

# --- manager control ----------------------------------------------------------
stop_run() {
  "${CORAL[@]}" stop >/dev/null 2>&1
  local drain=0
  while manager_alive && [ $drain -lt 180 ]; do sleep 10; drain=$((drain + 10)); done
}

# --- one launch+poll cycle ----------------------------------------------------
attempt_run() {
  local stop_file="$RUNDIR/.coral/public/auto_stop.json"
  rm -rf "$RUNDIR"

  local t0=$SECONDS
  "${CORAL[@]}" start -c "$TASK_YAML" \
    "agents.model=$MODEL" \
    "workspace.repo_path=$SEED_REPO" \
    "workspace.results_dir=./results/$CONDITION" \
    "workspace.run_dir=./results/$CONDITION/$RUNID" \
    "agents.heartbeat=[]" >/dev/null 2>&1 || { echo "start_failed"; return; }

  local waited=0
  while [ ! -f "$RUNDIR/.coral/config.yaml" ]; do
    sleep 5; waited=$((waited + 5))
    [ $waited -ge 300 ] && { echo "no_run_dir"; return; }
  done

  if ! wait_for_seed "$RUNDIR" || ! verify_condition "$RUNDIR"; then
    stop_run
    echo "condition_not_applied"
    return
  fi
  if ! verify_actual_model "$RUNDIR"; then
    stop_run
    echo "wrong_model"
    return
  fi
  log "  condition verified (model=$EXPECT_MODEL); polling every ${POLL_SEC}s"

  while :; do
    [ -f "$stop_file" ] && { echo "auto_stop"; return; }
    if rate_limited "$RUNDIR"; then
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

# --- main ---------------------------------------------------------------------
command -v uv >/dev/null || die "uv not found"
[ -f "$TASK_YAML" ] || die "missing $TASK_YAML"
[ -d "$SEED_REPO" ] || die "missing seed repo $SEED_REPO"
[ "$(git -C ../coral-upstream config core.autocrlf)" = "input" ] ||
  die "run: git -C coral-upstream config core.autocrlf input"
grep -q "knowledge: bool = True" ../coral-upstream/coral/config.py ||
  die "coral-upstream lacks agents.knowledge — check out the task3-ablation branch"
manager_alive && die "a CORAL manager is already running; \`coral stop\` first"
mkdir -p results

log "preflight OK — model=$MODEL (→ $EXPECT_MODEL via alias), condition=$CONDITION, $(nproc) cores, timeout ${TIMEOUT_SEC}s/run"

if [ -f "$RUNDIR/.coral/public/auto_stop.json" ]; then
  log "SKIP $RUNID ($CONDITION) — already finished"
  exit 0
fi

try=1 status=""
while [ $try -le "$MAX_TRIES" ]; do
  log "START $RUNID ($CONDITION) try $try/$MAX_TRIES"
  t0=$SECONDS
  status=$(attempt_run)
  elapsed=$((SECONDS - t0))
  n_attempts=$(find "$RUNDIR/.coral/public/attempts" -name '*.json' 2>/dev/null | wc -l)
  log "END   $RUNID ($CONDITION) status=$status elapsed=$((elapsed / 60))m attempts=$n_attempts"

  printf '{"runid":"%s","condition":"%s","model":"%s","try":%d,"status":"%s","elapsed_sec":%d,"attempts":%d,"run_dir":"%s","finished_at":"%s"}\n' \
    "$RUNID" "$CONDITION" "$MODEL" "$try" "$status" "$elapsed" "$n_attempts" \
    "results/$CONDITION/$RUNID" "$(date -Iseconds)" >>"$MANIFEST"

  [ "$status" = "auto_stop" ] && { log "ALL DONE — $RUNID finished cleanly"; log "next: uv run --project ../coral-upstream python analyze.py"; exit 0; }
  if [ "$status" = "rate_limited" ]; then
    wait_for_reset "$RUNDIR"
    try=$((try + 1))
    continue
  fi
  log "  $RUNID failed with status=$status"
  exit 1
done
log "  $RUNID exhausted $MAX_TRIES tries"
exit 1
