#!/usr/bin/env bash
#
# run_s3_batch.sh — run the three remaining s3 runs sequentially
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

SCRIPTS=(run_nohb_s3.sh run_nok_s3.sh run_full_s3.sh)

log "=== s3 batch starting: ${SCRIPTS[*]} ==="

for script in "${SCRIPTS[@]}"; do
  log "LAUNCH $script"
  ./"$script"
  rc=$?
  log "$script exited rc=$rc"

  # wait for manager to drain
  while manager_alive; do
    log "waiting for manager to drain..."
    sleep 30
  done
  sleep 60
done

log "=== s3 batch complete ==="
log "next: uv run --project ../coral-upstream python analyze.py"
