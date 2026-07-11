#!/usr/bin/env bash
#
# Task 3 — ablation driver.
#
# Runs the 9 ablation runs strictly sequentially. Sequential is not a convenience:
# the grader gives each solver a 10 s *wall-clock* budget per instance, so a second
# run competing for CPU would silently lower the score of whichever condition
# happened to be sharing the box. One run at a time, all 16 cores.
#
# All three conditions load the SAME task.yaml (../task2/task.yaml) and differ only
# by dotlist overrides, so task.description and task.tips — the text the agent
# actually reads — cannot drift between conditions.
#
#   full        vanilla CORAL (control)
#   noknowledge Condition A: agents.knowledge=false
#   noheartbeat Condition B: agents.heartbeat=[]
#
# Conditions are INTERLEAVED, not blocked, so drift over the ~18 h (thermal, API
# latency, model-side load) hits all three conditions alike.
#
# MODEL: sonnet, not opus. Two Opus agents exhaust the 5-hour API quota window in
# under 3 hours — the first attempt at this experiment died there, with 78
# `five_hour` rejections, agents crash-looping, and no run ever reaching its 12th
# real eval. The quota window is shared across models and Opus drains it several
# times faster. Every arm uses the same model, so the ablation comparison is
# unaffected; only the absolute scores are not comparable to Task 2's Opus run.
#
# Resumable: a run whose auto_stop.json already exists is skipped, so you can ^C
# this script and re-run it.
#
# Usage (from this directory, inside your own tmux/screen — it runs for hours):
#     ./run_ablation.sh              # all remaining runs
#     ./run_ablation.sh full-s1      # just one run id
#     MODEL=opus ./run_ablation.sh   # override the model (expect rate limits)
#
set -uo pipefail

cd "$(dirname "$0")" || exit 1

CORAL=(uv run --project ../coral-upstream coral)
TASK_YAML="../task2/task.yaml"
SEED_REPO="$(cd ../task2/seed && pwd)"
MODEL=${MODEL:-sonnet}
TIMEOUT_SEC=${TIMEOUT_SEC:-14400} # 4 h per run
POLL_SEC=${POLL_SEC:-60}
MAX_TRIES=${MAX_TRIES:-2} # retries after a rate-limit kill
MANIFEST="results/manifest.jsonl"

# runid:condition — interleaved so time-of-day drift hits every arm
PLAN=(
  "full-s1:full"
  "nok-s1:noknowledge"
  "nohb-s1:noheartbeat"
  "nok-s2:noknowledge"
  "nohb-s2:noheartbeat"
  "full-s2:full"
  "nok-s3:noknowledge"
  "nohb-s3:noheartbeat"
  "full-s3:full"
)

# stdout of attempt_run IS its return value (`status=$(attempt_run ...)`), so
# log() must never write there — otherwise status becomes "[HH:MM:SS] ...\nauto_stop"
# and the `status = auto_stop` test silently fails on a run that finished fine.
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { printf '\n!! %s\n' "$*" >&2; exit 1; }

# The handoff's gotcha: `pgrep -f "coral.cli start"` matches this script's own
# command line. The manager is always `python -m coral.cli start`; the bracket
# keeps the grep from matching itself.
manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

overrides_for() {
  case "$1" in
    full) : ;;
    noknowledge) echo "agents.knowledge=false" ;;
    noheartbeat) echo "agents.heartbeat=[]" ;;
    *) die "unknown condition: $1" ;;
  esac
}

# --- API quota handling ------------------------------------------------------
# A rate-limited agent does not stop: it exits 1, the manager restarts it, the
# crash-burst breaker pauses it, and the run burns wall clock producing nothing.
# Detect it, kill the run, wait for the window, retry from scratch.

rate_limited() {
  grep -rlq --include='*.log' '"status":"rejected"' "$1/.coral/public/logs" 2>/dev/null
}

# Agents log the window reset as a unix epoch: {"resetsAt":1783683600,...}
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
  local secs=$((epoch - now + 120)) # +2 min of slack
  log "  quota resets at $(date -d "@$epoch" +%H:%M:%S) — sleeping ${secs}s ($((secs / 60))m)"
  sleep "$secs"
}

# `.coral/config.yaml` lands in create_project, but the heartbeat JSONs are not
# seeded until AgentManager.start() — after the grader venv install. Verifying
# too early would fail on a file that simply has not been written yet.
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

# Assert the condition actually took effect before spending hours on the run.
verify_condition() {
  local rundir="$1" cond="$2" cfg="$1/.coral/config.yaml"
  [ -f "$cfg" ] || { log "  !! no config.yaml written"; return 1; }
  local pub="$rundir/.coral/public"
  grep -q "model: $MODEL" "$cfg" || { log "  !! model is not $MODEL"; return 1; }
  case "$cond" in
    full)
      grep -q "knowledge: true" "$cfg" || { log "  !! knowledge not true"; return 1; }
      [ -d "$pub/notes" ] && [ -d "$pub/skills" ] || { log "  !! notes/skills missing"; return 1; }
      grep -q "consolidate" "$pub/heartbeat/_global.json" || { log "  !! no global heartbeat"; return 1; }
      ;;
    noknowledge)
      grep -q "knowledge: false" "$cfg" || { log "  !! knowledge not false"; return 1; }
      for d in notes skills roles agents; do
        [ -e "$pub/$d" ] && { log "  !! $pub/$d exists"; return 1; }
      done
      grep -q "consolidate" "$pub/heartbeat/_global.json" 2>/dev/null &&
        { log "  !! consolidate still registered"; return 1; }
      ;;
    noheartbeat)
      # `[]` in a shell string is glob-adjacent; this is where we find out.
      grep -qE "heartbeat: \[\]" "$cfg" || { log "  !! heartbeat list not empty in config"; return 1; }
      for f in "$pub"/heartbeat/*.json; do
        [ -f "$f" ] || continue
        grep -q '"name"' "$f" && { log "  !! heartbeat actions in $(basename "$f")"; return 1; }
      done
      ;;
  esac
  return 0
}

# `agents.model=sonnet` is only a runtime *alias*. ~/.claude/settings.json's env
# block can remap it (ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro is how
# full-s1/nok-s1 silently ran on deepseek while their config.yaml said "sonnet").
# config.yaml records the alias; only the agent logs record what actually loaded.
# Derive the expected real-model prefix from MODEL so the documented
# `MODEL=opus ./run_ablation.sh` override is verified against claude-opus, not sonnet.
case "$MODEL" in
  sonnet) EXPECT_MODEL=${EXPECT_MODEL:-claude-sonnet} ;;
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
    *) log "  !! actual model is '$m', expected *${EXPECT_MODEL}* — check ANTHROPIC_DEFAULT_*_MODEL"; return 1 ;;
  esac
}

stop_run() {
  "${CORAL[@]}" stop >/dev/null 2>&1
  local drain=0
  while manager_alive && [ $drain -lt 180 ]; do sleep 10; drain=$((drain + 10)); done
}

# One launch+poll cycle. Echoes the final status.
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

  if ! wait_for_seed "$rundir" || ! verify_condition "$rundir" "$cond"; then
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
    return 1 # start_failed / condition_not_applied / timeout / manager_died
  done
  log "  $runid exhausted $MAX_TRIES tries"
  return 1
}

# --- preflight ---------------------------------------------------------------
command -v tmux >/dev/null || die "tmux not found"
command -v uv >/dev/null || die "uv not found"
[ -f "$TASK_YAML" ] || die "missing $TASK_YAML"
[ -d "$SEED_REPO" ] || die "missing seed repo $SEED_REPO"
# Without this, `coral start` dies with no logs: git describe --dirty must hash
# ~3,577 CRLF-dirty files and blows setuptools-scm's 40 s timeout.
[ "$(git -C ../coral-upstream config core.autocrlf)" = "input" ] ||
  die "run: git -C coral-upstream config core.autocrlf input"
# Condition A needs the fork's ablation flag; vanilla CORAL has no such field.
grep -q "knowledge: bool = True" ../coral-upstream/coral/config.py ||
  die "coral-upstream lacks agents.knowledge — check out the task3-ablation branch"
manager_alive && die "a CORAL manager is already running; \`coral stop\` first"
mkdir -p results
log "preflight OK — model=$MODEL, $(nproc) cores, timeout ${TIMEOUT_SEC}s/run"

only="${1:-}"
failed=0
for entry in "${PLAN[@]}"; do
  runid="${entry%%:*}"; cond="${entry##*:}"
  [ -n "$only" ] && [ "$only" != "$runid" ] && continue
  run_one "$runid" "$cond" || { failed=$((failed + 1)); log "  run $runid did not complete cleanly"; }
  sleep 60 # let the box settle (grader daemon teardown, page cache)
done

log "ALL DONE — $failed run(s) did not reach auto_stop"
log "next: uv run --project ../coral-upstream python analyze.py"
exit $((failed > 0))
