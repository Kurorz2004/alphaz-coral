#!/usr/bin/env bash
#
# monitor_and_s3.sh — monitor nohb-s1, then launch s3 batch when done
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

POLL_SEC=300  # check every 5 min
RUNDIR="results/noheartbeat/nohb-s1"
STOP_FILE="$RUNDIR/.coral/public/auto_stop.json"

manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

rate_limited() {
  grep -rlq --include='*.log' '"status":"rejected"' "$RUNDIR/.coral/public/logs" 2>/dev/null
}

log "=== monitor started — watching nohb-s1 ==="

while :; do
  if [ -f "$STOP_FILE" ]; then
    n_attempts=$(find "$RUNDIR/.coral/public/attempts" -name '*.json' 2>/dev/null | wc -l)
    log "nohb-s1 FINISHED — auto_stop.json present, $n_attempts attempts"
    break
  fi

  if rate_limited "$RUNDIR"; then
    log "!! nohb-s1 is rate-limited — keep waiting (run script handles retry)"
    sleep "$POLL_SEC"
    continue
  fi

  if ! manager_alive; then
    sleep 20
    if [ -f "$STOP_FILE" ]; then
      log "nohb-s1 FINISHED (manager stopped, stop file appeared)"
      break
    fi
    if ! manager_alive; then
      log "!! manager died AND no auto_stop.json — nohb-s1 may have failed"
      break
    fi
  fi

  n_attempts=$(find "$RUNDIR/.coral/public/attempts" -name '*.json' 2>/dev/null | wc -l)
  n_hb=$(find "$RUNDIR/.coral/public/heartbeat" -name '*.json' 2>/dev/null | wc -l)
  log "nohb-s1 running: attempts=$n_attempts heartbeat_files=$n_hb"
  sleep "$POLL_SEC"
done

# --- S3 batch ---------------------------------------------------------------
log "=== starting s3 batch (nohb-s3, nok-s3, full-s3) ==="

for script in run_nohb_s3.sh run_nok_s3.sh run_full_s3.sh; do
  # skip if already done
  case "$script" in
    run_nohb_s3.sh) sid="nohb-s3";;
    run_nok_s3.sh)  sid="nok-s3";;
    run_full_s3.sh) sid="full-s3";;
  esac

  if [ -f "results/${sid%%-*}/${sid}/.coral/public/auto_stop.json" ] 2>/dev/null; then
    log "SKIP $script — already finished"
    continue
  fi

  # wait for manager to be free (previous run's teardown)
  while manager_alive; do
    log "waiting for previous manager to exit..."
    sleep 30
  done
  sleep 60  # let box settle

  log "LAUNCH $script"
  ./"$script"
  rc=$?
  log "$script exited with rc=$rc"
  [ $rc -ne 0 ] && log "!! $script failed (rc=$rc) — continuing with next anyway"
done

log "=== s3 batch complete ==="
log "next: uv run --project ../coral-upstream python analyze.py"
